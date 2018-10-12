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

import copy
import glob
import logging
import os
import platform
import re
import warnings
from ast import literal_eval
from collections import namedtuple

import hcl
from colorama import init

from .utils import RecursiveDictionary

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
warnings.simplefilter('always', PendingDeprecationWarning)

if platform.platform().lower() == 'windows':
    init(convert=True)
else:
    init()


HclFileResource = namedtuple('HclFileResource', ('filename', 'resource_type', 'resource_name', 'data'))


class HclView(object):
    """Object representing the global view of hcl resources along with any global variables"""

    def __init__(self, hcl_resources, global_variables=None):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.state = RecursiveDictionary()
        if global_variables and isinstance(global_variables, dict):
            self.state.update({'variable': global_variables})
        for hcl_resource in hcl_resources:
            self._add_hcl_resource(hcl_resource)
        self.resources = self._interpolate_state(copy.deepcopy(self.state.get('resource')))

    def _add_hcl_resource(self, data):
        self.state.update(self._filter_empty_variables(data))

    @staticmethod
    def _filter_empty_variables(data):
        if 'variable' not in data.keys():
            return data
        data['variable'] = {key: value.get('default')
                            for key, value in data.get('variable').items() if value}
        return data

    def _interpolate_state(self, state):
        for _, resources_entries in state.items():
            for resource_name, resource_data in resources_entries.items():
                counter = resource_data.get('count')
                if counter:
                    del resources_entries[resource_name]
                    del resource_data['count']
                    for number in range(counter):
                        name = resource_name + '.{}'.format(number)
                        data = self._interpolate_counter(copy.deepcopy(resource_data), str(number))
                        resources_entries[name] = data
        state = self._interpolate_value(state)
        return state

    def _interpolate_value(self, data):
        for key, value in data.items():
            if isinstance(key, basestring):
                key = self._interpolate_variable(key)
            if isinstance(value, basestring):
                value = self._interpolate_variable(value)
            elif isinstance(value, dict):
                value = self._interpolate_value(value)
            data[key] = value
        return data

    def _interpolate_counter(self, data, number):
        for key, value in data.items():
            key = key.replace('count.index', number)
            if isinstance(value, basestring):
                value = value.replace('count.index', number)
            if isinstance(value, dict):
                value = self._interpolate_counter(value, number)
            data[key] = value
        return data

    @staticmethod
    def _interpolate_format(value):
        match = re.search(r'\(.*\)', value)  # look for '(' ending in ')' pattern
        if match:
            contents = match.group(0)[1:-1]
            value, argument = contents.split(',')
            argument = eval(argument, {"__builtins__": {}})  # pylint: disable=eval-used
            value = eval(' % '.join([value, str(argument)]), {"__builtins__": {}})  # pylint: disable=eval-used
        return value

    def _interpolate_variable(self, value):
        match = re.search(r'\$\{.*\}', value)  # look for '${' ending in '}' pattern
        if match:
            regex = match.group(0)
            if regex.startswith('${var.'):
                interpolated_value = self.get_variable_value(regex)
                if interpolated_value == regex:
                    self._logger.error('Could not interpolate variable "{}" maybe not set in variables?'.format(value))
                value = value.replace(regex, interpolated_value)
            elif '${format(' in regex:
                value = self._interpolate_format(value)
        return value

    def get_variable_value(self, value):
        """Retrieves the value of a variable from the global view of variables"""
        if value.startswith('${var.'):
            variable_name = value.split('var.')[1].split('}')[0]
            match = re.search(r'\[.*\]', variable_name)  # look for '[' ending in ']' pattern
            if match:
                name = variable_name.split('[')[0]
                value = self.state.get('variable', {}).get(name, value)
                if isinstance(value, dict):
                    key = literal_eval(match.group(0))[0]
                    value = value.get(key)
                elif isinstance(value, list):
                    index = literal_eval(match.group(0))[0]
                    value = value[index]
            else:
                value = self.state.get('variable', {}).get(variable_name, value)
        return value

    def get_resource_data_by_type(self, resource_type, resource_name):
        """Retrieves the data of a resource from the global hcl state based on its type."""
        return self.resources.get(resource_type, {}).get(resource_name)

    def get_counter_resource_data_by_type(self, resource_type, resource_name):  # pylint: disable=invalid-name
        """Retrieves the data of a resource from the global hcl state based on its type that has a count."""
        return [data for resource, data in self.resources.get(resource_type, {}).items()
                if resource.startswith(resource_name)]


class Parser(object):  # pylint: disable=too-few-public-methods
    """Manages the parsing of terraform files and creating the global hcl view from them"""

    def __init__(self, configuration_path, global_variables_file_path=None):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        file_resources, hcl_resources = self._parse_path(configuration_path)
        self.hcl_view = HclView(file_resources, self._get_global_variables(global_variables_file_path))
        self.file_resources = file_resources
        self.hcl_resources = hcl_resources

    def _get_global_variables(self, global_variables_file):
        if not global_variables_file:
            return {}
        try:
            global_variables_file_path = os.path.expanduser(global_variables_file)
            global_variables = hcl.load(open(global_variables_file_path, 'r'))
        except ValueError:
            self._logger.warning('Could not parse %s for resources', global_variables_file)
            global_variables = {}
        return global_variables

    def _parse_path(self, path):
        hcl_resources = []
        file_resources = []
        path = os.path.expanduser(os.path.join(path, '*.tf'))
        for tf_file_path in glob.glob(path):
            _, _, filename = tf_file_path.rpartition(os.path.sep)
            try:
                self._logger.debug('Trying to load file :%s', tf_file_path)
                data = hcl.load(open(tf_file_path, 'r'))
                file_resources.append(data)
                for resource_type, resource in data.get('resource', {}).items():
                    for resource_name, resource_data in resource.items():
                        hcl_resources.append(HclFileResource(filename, resource_type, resource_name, resource_data))
            except ValueError:
                self._logger.debug('Could not parse %s for resources', filename)
        return file_resources, hcl_resources
