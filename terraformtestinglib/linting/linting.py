#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: linting.py
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
Main code for linting

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import logging
import os
import re
import warnings

import yaml
from yaml.parser import ParserError
from schema import SchemaError

from terraformtestinglib.terraformtestinglib import Parser
from terraformtestinglib.configuration import NAMING_SCHEMA, POSITIONING_SCHEMA
from terraformtestinglib.terraformtestinglibexceptions import InvalidNaming, InvalidPositioning
from terraformtestinglib.utils import RuleError, ResourceError, FilenameError

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
LOGGER_BASENAME = '''linting'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.addHandler(logging.NullHandler())


class Stack(Parser):
    """Manages a stack as a collection of resources that can be checked for name convention"""

    def __init__(self,  # pylint: disable=too-many-arguments
                 configuration_path,
                 naming_file_path,
                 positioning_file_path=None,
                 global_variables_file_path=None,
                 file_to_skip_for_positioning=None,
                 raise_on_missing_variable=True):
        super(Stack, self).__init__(configuration_path, global_variables_file_path, raise_on_missing_variable)
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.path = configuration_path
        self.rules_set = self._get_naming_rules(naming_file_path)
        self.positioning = self._get_positioning_rules(positioning_file_path)
        self.positioning_skip_file = file_to_skip_for_positioning
        self.resources = self._get_resources()
        self._errors = []

    @staticmethod
    def _get_naming_rules(rules_file):
        try:
            rules_path_file = os.path.expanduser(rules_file)
            with open(rules_path_file, 'r') as rules_file_handle:
                rules = yaml.load(rules_file_handle.read())
                rules_file_handle.close()
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
            with open(positioning_path_file, 'r') as positioning_file_handle:
                positioning = yaml.load(positioning_file_handle.read())
                positioning_file_handle.close()
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
        for hcl_resource in self.hcl_resources:
            if hcl_resource.data.get('count'):
                for data in self.hcl_view.get_counter_resource_data_by_type(hcl_resource.resource_type,
                                                                            hcl_resource.resource_name):
                    resources.append(self._instantiate_resource(hcl_resource.filename,
                                                                hcl_resource.resource_type,
                                                                hcl_resource.resource_name,
                                                                data,
                                                                hcl_resource.data))
            else:
                resources.append(self._instantiate_resource(hcl_resource.filename,
                                                            hcl_resource.resource_type,
                                                            hcl_resource.resource_name,
                                                            self.hcl_view.get_resource_data_by_type(
                                                                hcl_resource.resource_type,
                                                                hcl_resource.resource_name),
                                                            hcl_resource.data))
        return resources

    def _instantiate_resource(self, filename, resource_type, name, data, original_data):  # pylint: disable=too-many-arguments
        resource = LintingResource(filename, resource_type, name, data, original_data)
        resource.register_rules_set(self.rules_set)
        if filename == self.positioning_skip_file:
            resource.register_positioning_set(None)
        else:
            resource.register_positioning_set(self.positioning)
        return resource

    def validate(self):
        """Validates all the resources of the stack

        Returns:
            None

        """
        self._errors = []
        for resource in self.resources:
            resource.validate()
            for error in resource.errors:
                self._errors.append(error)

    @property
    def errors(self):
        """The errors of the validation of the resources of the stack

        Returns:
            errors (ResourceError|FilenameError) : list of possible linting errors

        """
        return self._errors


class LintingResource:  # pylint: disable=too-many-instance-attributes
    """Manages a resource and provides validation capabilities."""

    def __init__(self, filename, resource_type, name, data, original_data):  # pylint: disable=too-many-arguments
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.filename = filename
        self.name = name
        self.type = resource_type
        self.data = data
        self.original_data = original_data
        self.rules_set = None
        self.positioning_set = None
        self.errors = None

    def __getattr__(self, value):
        return self.data.get(value)

    def register_rules_set(self, rules_set):
        """Registers the set of rules with the Resource.

        Args:
            rules_set (dict): A dictionary with the rules for the naming convention

        Returns:
            None

        """
        self.rules_set = rules_set

    def register_positioning_set(self, positioning_set):
        """Registers the set of rules with the Resource.

        Args:
            positioning_set (dict): A dictionary with the rules for the positioning convention

        Returns:
            None

        """
        self.positioning_set = positioning_set

    def _get_entity_desired_filename(self, entity):
        target = next((filename for filename, entities in self.positioning_set.items()
                       if entity in entities), 'unknown')
        return target

    def validate(self):
        """Validates the resource according to the appropriate rule.

        Returns:
            True upon completion

        """
        self.errors = []
        validate_positioning = True
        if not self.rules_set:
            self._logger.warning('No rules set!')
            return True
        if self.positioning_set is None:
            message = ('Skipping resource positioning due to positioning file not been provided or '
                       'being skipped.')
            self._logger.info(message)
            validate_positioning = False
        elif os.environ.get('SKIP_POSITIONING'):
            self._logger.info('Skipping resource positioning due to global environment setting.')
            validate_positioning = False
        self._logger.debug('Resource type %s', self.type)
        self._validate_naming()
        if validate_positioning:
            self._validate_positioning()
        return True

    def _is_check_skipped(self, tag_name, deprecated_tag_name=None):
        skip_check = False
        try:
            check_tag = tag_name
            deprecated_tag = deprecated_tag_name
            tags = self.tags or {}
            if tags.get(deprecated_tag):
                message = ('The tag "{}" is deprecated. '
                           'Please use "{}". Resource: {}').format(deprecated_tag, check_tag, self.name)
                warnings.warn(message, PendingDeprecationWarning)
                check_tag = deprecated_tag
            skip_check = tags.get(check_tag, False)
        except IndexError:
            self._logger.error(('Weird error with no or broken resources '
                                'found %s for resource %s' % self.data, self.name))
        except AttributeError:
            self._logger.exception('Multiple tags entry found on resource %s', self.name)
        return skip_check

    def _validate_positioning(self):
        self._logger.debug('Resource name %s', self.name)
        if self._is_check_skipped('skip-positioning', 'skip_positioning'):
            self._logger.warning('Skipping resource %s positioning checking '
                                 'due to user overriding tag.', self.name)
        else:
            full_desired_filename = self._get_entity_desired_filename(self.type)
            desired_filename, _, _ = full_desired_filename.rpartition('.tf')
            file_name, _, _ = self.filename.rpartition('.')
            if not re.match(desired_filename, file_name):
                self.errors.append(FilenameError(self.filename, self.name, full_desired_filename))
                self._logger.error('Filename positioning not followed on file %s for resource '
                                   '%s. Should be in a file matching %s.tf .',
                                   self.filename,
                                   self.name,
                                   desired_filename)
        return True

    def _validate_naming(self):
        self._logger.debug('Resource name %s', self.name)
        if self._is_check_skipped('skip-linting', 'skip_linting'):
            self._logger.warning('Skipping resource %s naming checking '
                                 'due to user overriding tag.', self.name)
        else:
            rule = self.rules_set.get_rule_for_resource(self.type)
            if rule:
                self._logger.debug('Found matching rule "%s"', rule.regex)
                rule.validate(self.type, self.name, self.data, self.original_data)
                for error in rule.errors:
                    self._logger.error('Naming convention not followed on file %s for resource '
                                       '%s with type %s. Regex not matched :%s. Value :%s',
                                       self.filename,
                                       error.entity,
                                       error.field,
                                       error.regex,
                                       error.value)
                    self.errors.append(ResourceError(self.filename, *error))
            else:
                self._logger.debug('No matching rule found')
        return True


class RuleSet:  # pylint: disable=too-few-public-methods
    """Manages the rules as a group and can search them by name."""

    def __init__(self, rules):
        self._rules = rules

    def get_rule_for_resource(self, resource_name):
        """Retrieves the rule for the resource name

        Args:
            resource_name (basestring): The resource type to retrieve the rule for

        Returns:
            The rule corresponding with the resource type if found, None otherwise

        """
        return next((Rule(rule) for rule in self._rules
                     if rule.get('resource') == resource_name), None)


class Rule:
    """Handles the rule object providing validation capabilities."""

    def __init__(self, data):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.data = data
        self.regex = self.data.get('regex')
        self._errors = []

    @property
    def errors(self):
        """List of errors found

        Returns: The errors found

        """
        return self._errors

    @errors.setter
    def errors(self, error):
        self._errors.append(error)

    def validate(self, resource_type, resource_name, resource_data, original_data):
        """Validates the given resource based on the ruleset.

        Args:
            resource_type (basestring): The type of the resource
            resource_name (basestring): The name of the resource
            resource_data (dict): The interpolated data of the resource
            original_data (dict): The origininal data of the resource, before the interpolation

        Returns:
            True on successful validation, False otherwise

        """
        if not self.regex:
            return True
        self._validate_name(resource_type, resource_name)
        self._validate_values(resource_type, resource_name, resource_data, original_data)
        return True if not self.errors else False

    def _validate_name(self, resource_type, resource_name):
        rule = re.compile(self.regex)
        if not re.match(rule, resource_name):
            self.errors = RuleError(resource_type, resource_name, 'id', self.regex, resource_name, None)

    def _validate_values(self, resource_type, resource_name, resource_data, original_data):
        for field in self.data.get('fields', []):
            regex = field.get('regex')
            if not regex:
                continue
            rule = re.compile(regex)
            original_value = self._get_value_from_resource(original_data, field.get('value'))
            value = self._get_value_from_resource(resource_data, field.get('value'))
            original_value = original_value if original_value != value else None
            rule_arguments = [resource_type, resource_name, field.get('value'), regex, value, original_value]
            try:
                if not re.match(rule, value):
                    self.errors = RuleError(*rule_arguments)
            except TypeError:
                self._logger.error('Error matching for regex, values passed were, rule:%s value:%s', regex, value)

    def _get_value_from_resource(self, resource, value):
        path = value.split('.')
        for entry in path:
            try:
                field = resource.get(entry)
            except AttributeError:
                field = None
                self._logger.error('Error getting field %s, failed for path %s', value, path)
            resource = field
        return resource
