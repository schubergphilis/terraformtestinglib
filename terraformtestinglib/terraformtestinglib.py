#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: terraformtestinglib.py
#
# Copyright 2018 Costas Tyfoxylos
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
#

"""
Main code for terraformtestinglib

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import glob
import logging
import os
import platform
import re
import warnings

import hcl
import yaml
from yaml.parser import ParserError
from colorama import init
from schema import SchemaError


from .configuration import NAMING_SCHEMA, POSITIONING_SCHEMA
from .errortypes import RuleError, ResourceError, FilenameError
from .terraformtestinglibexceptions import InvalidNaming, InvalidPositioning

__author__ = '''Costas Tyfoxylos <ctyfoxylos@schubergphilis.com>'''
__docformat__ = '''google'''
__date__ = '''2018-05-24'''
__copyright__ = '''Copyright 2018, Costas Tyfoxylos'''
__credits__ = ["Costas Tyfoxylos"]
__license__ = '''MIT'''
__maintainer__ = '''Costas Tyfoxylos'''
__email__ = '''<ctyfoxylos@schubergphilis.com>'''
__status__ = '''Development'''  # "Prototype", "Development", "Production".


# This is the main prefix used for logging
LOGGER_BASENAME = '''terraformtestinglib'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.addHandler(logging.NullHandler())


def warning_on_one_line(message, category, *rest_args):  # pylint: disable=unused-argument
    """Warning formating method"""
    return '\n\n%s:%s\n\n' % (category.__name__, message)


warnings.formatwarning = warning_on_one_line

if platform.platform().lower() == 'windows':
    init(convert=True)
else:
    init()


class Stack(object):
    """Manages a stack as a collection of resources that can be checked for name convention"""

    def __init__(self, configuration_path, naming_file_path, positioning_file_path=None):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.path = configuration_path
        self.rules_set = self._get_naming_rules(naming_file_path)
        self.positioning = self._get_positioning_rules(positioning_file_path)
        self.resources = self._get_resources()
        self._errors = []

    @staticmethod
    def _get_naming_rules(rules_file):
        try:
            rules_path_file = os.path.expanduser(rules_file)
            rules = yaml.load(open(rules_path_file, 'r').read())
            rules = NAMING_SCHEMA.validate(rules)
        except IOError:
            raise InvalidNaming('Could not load naming file')
        except ParserError:
            raise InvalidNaming('Unable to parse yaml file. Please check that it is valid.')
        except SchemaError as error:
            raise InvalidNaming(error)
        return RuleSet(rules)

    @staticmethod
    def _get_positioning_rules(positioning_file):
        if positioning_file is None:
            return None
        try:
            positioning_path_file = os.path.expanduser(positioning_file)
            positioning = yaml.load(open(positioning_path_file, 'r').read())
            positioning = POSITIONING_SCHEMA.validate(positioning)
        except IOError:
            raise InvalidPositioning('Could not load positioning file')
        except ParserError:
            raise InvalidPositioning('Unable to parse yaml file. Please check that it is valid.')
        except SchemaError as error:
            raise InvalidPositioning(error)
        return positioning

    def _get_resources(self):
        resources = []
        path = os.path.expanduser(os.path.join(self.path, '*.tf'))
        for tf_file_path in glob.glob(path):
            _, _, filename = tf_file_path.rpartition(os.path.sep)
            try:
                self._logger.debug('Trying to load file :%s', tf_file_path)
                data = hcl.load(open(tf_file_path, 'r'))
                resourse = Resource(filename, data)
                resourse.register_rules_set(self.rules_set)
                resourse.register_positioning_set(self.positioning)
                resources.append(resourse)
            except ValueError:
                self._logger.error('Could not parse %s for resources', filename)

        return resources

    def validate(self):
        """Validates all the resources of the stack"""
        self._errors = []
        for resource in self.resources:
            resource.validate()
            for error in resource.errors:
                self._errors.append(error)

    @property
    def errors(self):
        """The errors of the validation of the resources of the stack"""
        return self._errors


class Resource(object):
    """Manages a resource and provides validation capabilities."""

    def __init__(self, filename, data):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.filename = filename
        self.data = data
        self.rules_set = None
        self.positioning_set = None
        self.errors = None

    def __getattr__(self, value):
        return self.data.get('resource', {}).get(value)

    def register_rules_set(self, rules_set):
        """Registers the set of rules with the Resource."""
        self.rules_set = rules_set

    def register_positioning_set(self, positioning_set):
        """Registers the set of rules with the Resource."""
        self.positioning_set = positioning_set

    def _get_entity_desired_filename(self, entity):
        target = next((filename for filename, entities in self.positioning_set.items()
                       if entity in entities), 'unknown')
        return target

    def validate(self):
        """Validates the resource according to the appropriate rule."""
        self.errors = []
        validate_positioning = True
        if not self.rules_set:
            self._logger.warning('No rules set!')
            return True
        resource = self.data.get('resource')
        if self.positioning_set is None:
            self._logger.info('Skipping resource positioning due to positioning file not been provided.')
            validate_positioning = False
        elif os.environ.get('SKIP_POSITIONING'):
            self._logger.info('Skipping resource positioning due to global environment setting.')
            validate_positioning = False
        if resource:
            for resource_type, resource_data in resource.items():
                self._logger.debug('Found resource type %s', resource_type)
                self._validate_naming(resource_type, resource_data)
                if validate_positioning:
                    self._validate_positioning(resource_type, resource_data)
        return True

    def _is_check_skipped(self, resource_name, resource_data, tag_name, deprecated_tag_name=None):
        skip_check = False
        try:
            check_tag = tag_name
            deprecated_tag = deprecated_tag_name
            tags = resource_data.get('tags', {})
            if tags.get(deprecated_tag) is not None:
                message = ('The tag "{}" is deprecated. '
                           'Please use "{}". Resource: {}').format(deprecated_tag, check_tag, resource_name)
                warnings.warn(message, PendingDeprecationWarning)
                check_tag = deprecated_tag
            skip_check = tags.get(check_tag, False)
        except IndexError:
            self._logger.error(('Weird error with no or broken resources '
                                'found %s for resource %s' % resource_data, resource_name))
        except AttributeError:
            self._logger.exception('Multiple tags entry found on resource %s', resource_name)
        return skip_check

    def _validate_positioning(self, resource_type, resource):
        if resource:
            for resource_name, resource_data in resource.items():
                self._logger.debug('Found resource %s', resource_name)
                if self._is_check_skipped(resource_name, resource_data, 'skip-positioning', 'skip_positioning'):
                    self._logger.warning('Skipping resource %s positioning checking '
                                         'due to user overriding tag.', resource_name)
                else:
                    full_desired_filename = self._get_entity_desired_filename(resource_type)
                    desired_filename, _, _ = full_desired_filename.rpartition('.tf')
                    file_name, _, _ = self.filename.rpartition('.')
                    if not re.match(desired_filename, file_name):
                        self.errors.append(FilenameError(self.filename, resource_name, full_desired_filename))
                        self._logger.error('Filename positioning not followed on file %s for resource '
                                           '%s. Should be in a file matching %s.tf .',
                                           self.filename,
                                           resource_name,
                                           desired_filename)
        return True

    def _validate_naming(self, resource_type, resource):
        if resource:
            for resource_name, resource_data in resource.items():
                self._logger.debug('Found resource %s', resource_name)
                if self._is_check_skipped(resource_name, resource_data, 'skip-linting', 'skip_linting'):
                    self._logger.warning('Skipping resource %s naming checking '
                                         'due to user overriding tag.', resource_name)
                else:
                    rule = self.rules_set.get_rule_for_resource(resource_type)
                    if rule:
                        self._logger.debug('Found matching rule "%s"', rule.regex)
                        rule.validate(resource_name, resource_data)
                        for error in rule.errors:
                            self._logger.error('Naming convention not followed on file %s for resource '
                                               '%s with type %s. Regex not matched :%s. Value :%s',
                                               self.filename,
                                               error.entity,
                                               error.field,
                                               error.regex,
                                               error.value)
                            self.errors.append(ResourceError(self.filename, resource_name, *error))
                    else:
                        self._logger.debug('No matching rule found')
        return True


class RuleSet(object):  # pylint: disable=too-few-public-methods
    """Manages the rules as a group and can search them by name."""

    def __init__(self, rules):
        self._rules = rules

    def get_rule_for_resource(self, resource_name):
        """Retrieves the rule for the resource name"""
        return next((Rule(rule) for rule in self._rules
                     if rule.get('resource') == resource_name), None)


class Rule(object):
    """Handles the rule object providing validation capabilities."""

    def __init__(self, data):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.data = data
        self.regex = self.data.get('regex')
        self._errors = []

    @property
    def errors(self):
        """List of errors found"""
        return self._errors

    @errors.setter
    def errors(self, error):
        self._errors.append(error)

    def validate(self, resource_name, resource_data):
        """Validates the given resource based on the ruleset."""
        if not self.regex:
            return True
        self._validate_name(resource_name)
        self._validate_values(resource_name, resource_data)
        return True if not self.errors else False

    def _validate_name(self, resource_name):
        rule = re.compile(self.regex)
        if not re.match(rule, resource_name):
            self.errors = RuleError(resource_name, 'id', self.regex, resource_name)

    def _validate_values(self, resource_name, resource_data):
        for field in self.data.get('fields', []):
            regex = field.get('regex')
            if not regex:
                continue
            rule = re.compile(regex)
            value = self._get_value_from_resource(resource_data,
                                                  field.get('value'))
            try:
                if not re.match(rule, value):
                    self.errors = RuleError(resource_name, field.get('value'), regex, value)
            except TypeError:
                self._logger.error('Error matching for regex, values passed were, rule:%s value:%s', rule, value)

    def _get_value_from_resource(self, resource, value):
        path = value.split('.') or [value]
        for entry in path:
            try:
                field = resource.get(entry)
            except AttributeError:
                field = None
                self._logger.error('Error getting field %s, failed for path %s', value, path)
            resource = field
        return resource
