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

from .terraformtestinglibexceptions import MissingVariable
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


def warning_on_one_line(message, category, filename, lineno, line=None):  # pylint: disable=unused-argument
    """Warning formating method"""
    return '\n\n%s:%s\n\n' % (category.__name__, message)


warnings.formatwarning = warning_on_one_line
warnings.simplefilter('always', PendingDeprecationWarning)

if platform.platform().lower() == 'windows':
    init(convert=True)
else:
    init()


HclFileResource = namedtuple('HclFileResource', ('filename', 'resource_type', 'resource_name', 'data'))


class HclView:
    """Object representing the global view of hcl resources along with any global variables"""

    def __init__(self, hcl_resources, global_variables=None, raise_on_missing_variable=True):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        self.state = RecursiveDictionary()
        self._raise_on_missing_variable = raise_on_missing_variable
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
        output = {}
        for resources_type, resources_entries in state.items():
            entry = {}
            for resource_name, resource_data in resources_entries.items():
                counter = resource_data.get('count')
                if counter:
                    for number in range(counter):
                        name = resource_name + '.{}'.format(number)
                        data = self._interpolate_counter(copy.deepcopy(resource_data), str(number))
                        entry[name] = data
                else:
                    entry[resource_name] = resource_data
            output[resources_type] = entry
        state = self._interpolate_value(output)
        return state

    def _interpolate_value(self, data):
        output = {}
        for key, value in data.items():
            if isinstance(key, str):
                key = self._interpolate_variable(key)
            if isinstance(value, str):
                value = self._interpolate_variable(value)
            elif isinstance(value, dict):
                value = self._interpolate_value(value)
            output[key] = value
        return output

    def _interpolate_counter(self, data, number):
        output = {}
        for key, value in data.items():
            key = key.replace('count.index', number)
            if isinstance(value, str):
                value = value.replace('count.index', number)
            if isinstance(value, dict):
                value = self._interpolate_counter(value, number)
            output[key] = value
        return output

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

    def get_variable_value(self, variable):
        """Retrieves the value of a variable from the global view of variables

        Args:
            variable (): The variable to look for

        Raises:
            MissingValue : If the value does not exist

        Returns:

        """
        initial_value = variable
        if variable.startswith('${var.'):
            variable_name = variable.split('var.')[1].split('}')[0]
            match = re.search(r'\[.*\]', variable_name)  # look for '[' ending in ']' pattern
            if match:
                name = variable_name.split('[')[0]
                variable = self.state.get('variable', {}).get(name, variable)
                if isinstance(variable, dict):
                    key = literal_eval(match.group(0))[0]
                    variable = variable.get(key)
                elif isinstance(variable, list):
                    index = literal_eval(match.group(0))[0]
                    variable = variable[index]
            else:
                variable = self.state.get('variable', {}).get(variable_name, variable)
        if variable == initial_value and self._raise_on_missing_variable:
            raise MissingVariable(initial_value)
        return variable

    def get_resource_data_by_type(self, resource_type, resource_name):
        """Retrieves the data of a resource from the global hcl state based on its type.

        Args:
            resource_type (basestring): The resource type to retrieve the data for
            resource_name (basestring): The resource name to retrieve the data for

        Returns:
            Interpolated data (dict) for the provided resource name and resource type

        """
        return self.resources.get(resource_type, {}).get(resource_name)

    def get_counter_resource_data_by_type(self, resource_type, resource_name):
        """Retrieves the data of a resource from the global hcl state based on its type that has a count.

        Args:
            resource_type (basestring): The resource type to retrieve the data for
            resource_name (basestring): The resource name to retrieve the data for

        Returns:
            Original non interpolated data (dict) for the provided resource name and resource type

        """
        return [data for resource, data in self.resources.get(resource_type, {}).items()
                if resource.startswith(resource_name)]


class Parser:  # pylint: disable=too-few-public-methods
    """Manages the parsing of terraform files and creating the global hcl view from them"""

    def __init__(self, configuration_path, global_variables_file_path=None, raise_on_missing_variable=True):
        logger_name = u'{base}.{suffix}'.format(base=LOGGER_BASENAME, suffix=self.__class__.__name__)
        self._logger = logging.getLogger(logger_name)
        file_resources, hcl_resources = self._parse_path(configuration_path)
        self.hcl_view = HclView(file_resources,
                                self._get_global_variables(global_variables_file_path),
                                raise_on_missing_variable)
        self.file_resources = file_resources
        self.hcl_resources = hcl_resources

    def _get_global_variables(self, global_variables_file):
        if not global_variables_file:
            return {}
        try:
            global_variables_file_path = os.path.expanduser(global_variables_file)
            with open(global_variables_file_path, 'r') as globals_file:
                global_variables = hcl.load(globals_file)
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
                with open(tf_file_path, 'r') as terraform_file:
                    data = hcl.load(terraform_file)
                file_resources.append(data)
                for resource_type, resource in data.get('resource', {}).items():
                    for resource_name, resource_data in resource.items():
                        hcl_resources.append(HclFileResource(filename, resource_type, resource_name, resource_data))
            except ValueError:
                self._logger.debug('Could not parse %s for resources', filename)
        return file_resources, hcl_resources
