#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: test_terraformtestinglib.py
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
test_terraformtestinglib
----------------------------------
Tests for `terraformtestinglib` module.

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import warnings
import os

import unittest
from terraformtestinglib import Stack, Validator
from terraformtestinglib.terraformtestinglib import HclView
from terraformtestinglib.terraformtestinglibexceptions import InvalidNaming, InvalidPositioning, MissingVariable
from terraformtestinglib.configuration import is_valid_regex
from terraformtestinglib.utils import ResourceError, FilenameError

__author__ = '''Costas Tyfoxylos <ctyfoxylos@schubergphilis.com>'''
__docformat__ = '''google'''
__date__ = '''2018-05-24'''
__copyright__ = '''Copyright 2018, Costas Tyfoxylos'''
__credits__ = ["Costas Tyfoxylos"]
__license__ = '''MIT'''
__maintainer__ = '''Costas Tyfoxylos'''
__email__ = '''<ctyfoxylos@schubergphilis.com>'''
__status__ = '''Development'''  # "Prototype", "Development", "Production".


class TestLintingFeatures(unittest.TestCase):

    def setUp(self):
        """
        Test set up

        This is where you can setup things that you use throughout the tests. This method is called before every test.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.fixtures = os.path.join(current_dir, 'fixtures', 'linting')
        self.stack_path = os.path.join(self.fixtures, 'stack')
        self.naming_file = os.path.join(self.fixtures, 'naming.yaml')
        self.interpolated_naming_file = os.path.join(self.fixtures, 'interpolated_naming.yaml')
        self.count_interpolated_naming_file = os.path.join(self.fixtures, 'count_interpolated_naming.yaml')
        self.globals_file = os.path.join(self.stack_path, 'global.tfvars')
        self.broken_schema_naming_file = os.path.join(self.fixtures, 'broken_schema_naming.yaml')
        self.broken_yaml_naming_file = os.path.join(self.fixtures, 'broken_yaml_naming.yaml')
        self.positioning_file = os.path.join(self.fixtures, 'positioning.yaml')
        self.broken_schema_positioning_file = os.path.join(self.fixtures, 'broken_schema_positioning.yaml')
        self.broken_yaml_positioning_file = os.path.join(self.fixtures, 'broken_yaml_positioning.yaml')

    def test_regex_checking(self):
        self.assertFalse(is_valid_regex('['))

    def test_naming_file(self):
        self.assertRaises(InvalidNaming, Stack, self.stack_path, 'random/path', self.positioning_file,
                          self.globals_file)
        self.assertRaises(InvalidNaming, Stack, self.stack_path, self.broken_schema_naming_file, self.positioning_file,
                          self.globals_file)
        self.assertRaises(InvalidNaming, Stack, self.stack_path, self.broken_yaml_naming_file, self.positioning_file,
                          self.globals_file)

    def test_positioning_file(self):
        self.assertRaises(InvalidPositioning, Stack, self.stack_path, self.naming_file, 'random/path',
                          self.globals_file)
        self.assertRaises(InvalidPositioning, Stack, self.stack_path, self.naming_file,
                          self.broken_schema_positioning_file, self.globals_file)
        self.assertRaises(InvalidPositioning, Stack, self.stack_path, self.naming_file,
                          self.broken_yaml_positioning_file, self.globals_file)
        stack = Stack(self.stack_path, self.naming_file, None, self.globals_file)
        assert isinstance(stack, Stack)
        stack.validate()

    def test_global_positioning_skip(self):
        os.environ['SKIP_POSITIONING'] = "true"
        stack = Stack(self.stack_path, self.naming_file, self.positioning_file, self.globals_file)
        stack.validate()
        for error in stack.errors:
            assert not isinstance(error, FilenameError)
        del os.environ['SKIP_POSITIONING']

    def test_positioning_errors(self):
        stack = Stack(self.stack_path, self.naming_file, self.positioning_file, self.globals_file)
        stack.validate()
        assert len([error for error in stack.errors if isinstance(error, FilenameError)]) == 2

    def test_naming_errors(self):
        stack = Stack(self.stack_path, self.naming_file, self.positioning_file, self.globals_file)
        stack.validate()
        assert len([error for error in stack.errors if isinstance(error, ResourceError)]) == 4

    def test_deprecated_warnings(self):
        with warnings.catch_warnings(record=True) as warnings_:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            self.stack = Stack(self.stack_path, self.naming_file, self.positioning_file, self.globals_file)
            self.stack.validate()
            assert len(warnings_) == 3
            for warning_ in warnings_:
                assert issubclass(warning_.category, PendingDeprecationWarning)

    def test_error_messages(self):
        stack = Stack(self.stack_path, self.naming_file, self.positioning_file, self.globals_file)
        stack.validate()
        for error in stack.errors:
            assert 'not followed on file' in str(error)

    def test_variable_interpolation(self):
        stack = Stack(self.stack_path, self.interpolated_naming_file, None, self.globals_file)
        stack.validate()
        for error in stack.errors:
            assert 'test_interpolated_value' in str(error)

    def test_count_interpolation(self):
        stack = Stack(self.stack_path, self.count_interpolated_naming_file, None, self.globals_file)
        stack.validate()
        assert len(stack.errors) == 4

    def tearDown(self):
        """
        Test tear down

        This is where you should tear down what you've setup in setUp before. This method is called after every test.
        """
        pass


class TestParsingFeatures(unittest.TestCase):

    def setUp(self):
        """
        Test set up

        This is where you can setup things that you use throughout the tests. This method is called before every test.
        """
        self.default_resources = [{'resource': {'aws_instance': {'foo': {'value2': 2, 'value': 1},
                                                                 'bar': {'value2': 2, 'value': 1}}}},
                                  {'resource': {'aws_instance': {'foo2': {'value3': 3, 'value4': 4},
                                                                 'bar2': {'value3': 3, 'value4': 4}}}}]
        self.default_global_variables = {'spam': 'eggs',
                                         'parrot': 'blah',
                                         'dict_var': {'aha': '!',
                                                      'more': '!!'},
                                         'list_var': ['one', 'two', 'three?']}

        self.hcl_view = HclView(self.default_resources, self.default_global_variables)

    def test_resource_parsing(self):
        assert len(self.hcl_view.resources.get('aws_instance').keys()) == 4

    def test_resource_exists(self):
        assert self.hcl_view.resources.get('aws_instance').get('bar2') == {'value4': 4, 'value3': 3}

    def test_simple_variable_interpolation(self):
        assert self.hcl_view.get_variable_value('${var.parrot}') == 'blah'

    def test_dict_variable_interpolation(self):
        assert self.hcl_view.get_variable_value('${var.dict_var["aha"]}') == '!'

    def test_list_variable_interpolation(self):
        assert self.hcl_view.get_variable_value('${var.list_var[1]}') == 'two'

    def test_missing_variables(self):
        self.assertRaises(MissingVariable, self.hcl_view.get_variable_value, '${var.not_existing}')

    def test_disable_missing_variables(self):
        hcl_view = HclView(self.default_resources, self.default_global_variables, raise_on_missing_variable=False)
        assert hcl_view.get_variable_value('${var.not_existing}') == '${var.not_existing}'


class TestTestingFeatures(unittest.TestCase):

    def setUp(self):
        """
        Test set up

        This is where you can setup things that you use throughout the tests. This method is called before every test.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        fixtures = os.path.join(current_dir, 'fixtures', 'testing')
        self.stack_path = os.path.join(fixtures, 'stack')
        self.globals_file = os.path.join(self.stack_path, 'global.tfvars')
        self.validator = Validator(self.stack_path, self.globals_file, raise_on_missing_variable=True)

    def test_resource_parsing(self):
        assert len(self.validator.resources('random_resource')._resources) == 1
        assert len(self.validator.resources(['random_resource', 'random_resource_other'])._resources) == 2
        assert len(self.validator.resources(['random_resource',
                                             'random_resource_other']).resources('random_resource')._resources) == 1
        assert len(self.validator.resources(['random_resource',
                                             'random_resource_other']).resources('random_resource')._resources) == 1

    def test_missing_variable(self):
        self.assertRaises(MissingVariable, self.validator.get_variable_value, '${var.non_existent}')

    def test_disable_missing_variable(self):
        validator = Validator(self.stack_path, self.globals_file, raise_on_missing_variable=False)
        assert validator.get_variable_value('${var.non_existent}') == '${var.non_existent}'

    def test_attribute_access(self):
        assert len(self.validator.resources('random_resource').attribute('tags').attributes) == 1

    def test_missing_attribute_access(self):
        assert self.validator.resources('random_resource').attribute('garbage').attributes == []

    def test_missing_attribute_access_raise(self):
        validator = Validator(self.stack_path, self.globals_file)
        validator.error_on_missing_attribute = True
        with self.assertRaises(AssertionError):
            validator.resources('random_resource').attribute('garbage')

    def test_variable_accessing(self):
        assert self.validator.variable('image-aws-rhel74').value == 'ami-bb9a6bc2'

    def test_regex_matching_attribute(self):
        assert self.validator.resources('random_resource').attribute_matching_regex('tag?').attributes[0].name == 'tags'

    def test_regex_matching_attribute_raise_on_missing(self):
        self.validator.error_on_missing_attribute = True
        with self.assertRaises(AssertionError):
            self.validator.resources('random_resource').attribute_matching_regex('garbage')
        self.validator.error_on_missing_attribute = False

    def test_attribute_raise_on_missing(self):
        self.validator.error_on_missing_attribute = True
        with self.assertRaises(AssertionError):
            self.validator.resources('random_resource').should_have_attributes(['garbage', 'more'])
        self.validator.error_on_missing_attribute = False

    def test_attribute_raise_on_existing(self):
        self.validator.error_on_missing_attribute = True
        with self.assertRaises(AssertionError):
            self.validator.resources('random_resource').should_not_have_attributes(['tags'])
        self.validator.error_on_missing_attribute = False

    def test_filtering_on_attribute(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_has_attribute('tags')._resources) == 3

    def test_filtering_on_missing_attribute(self):
        assert len(
            self.validator.resources('azurerm_virtual_machine').if_not_has_attribute('not_matching')._resources) == 2

    def test_filtering_on_attribute_with_value(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_has_attribute_with_value('not_matching',
                                                                                                   'true')._resources) == 1

    def test_filtering_on_attribute_not_with_value(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_not_has_attribute_with_value('not_matching',
                                                                                                       'false')._resources) == 1

    def test_filtering_on_attribute_with_regex_value(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_has_attribute_with_regex_value('not_matching',
                                                                                                         'tr.e')._resources) == 1

    def test_filtering_on_attribute_not_with_regex_value(self):
        assert len(
            self.validator.resources('azurerm_virtual_machine').if_not_has_attribute_with_regex_value('not_matching',
                                                                                                      'fal.e')._resources) == 1

    def test_filtering_on_subattribute(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_has_subattribute('tags',
                                                                                           'subattribute_test')._resources) == 2

    def test_filtering_on_missing_subattribute(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_not_has_subattribute('tags',
                                                                                               'subattribute_test')._resources) == 1

    def test_filtering_on_subattribute_with_value(self):
        assert len(self.validator.resources('azurerm_virtual_machine').if_has_subattribute_with_value('tags',
                                                                                                      'subattribute_test',
                                                                                                      'true')._resources) == 1
        assert len(self.validator.resources('azurerm_virtual_machine').if_not_has_subattribute_with_value('tags',
                                                                                                          'subattribute_test',
                                                                                                          'true')._resources) == 2
        assert len(self.validator.resources('azurerm_virtual_machine').if_not_has_subattribute_with_value('tags',
                                                                                                          'subattribute_test',
                                                                                                          'false')._resources) == 2

    def test_filtering_on_subattribute_with_regex_value(self):
        self.validator.error_on_missing_attribute = False
        assert len(self.validator.resources('azurerm_virtual_machine').if_has_subattribute_with_regex_value('tags',
                                                                                                            'subattribute_test',
                                                                                                            'tr.e')._resources) == 1
        assert len(self.validator.resources('azurerm_virtual_machine').if_not_has_subattribute_with_regex_value('tags',
                                                                                                                'subattribute_test',
                                                                                                                'tr.e')._resources) == 1
        assert len(self.validator.resources('azurerm_virtual_machine').if_not_has_subattribute_with_regex_value('tags',
                                                                                                                'subattribute_test',
                                                                                                                'fal.e')._resources) == 1
        self.validator.error_on_missing_attribute = True

    def test_nested_attributes(self):
        assert len(self.validator.resources('azurerm_virtual_machine').attribute('tags').attribute('subattribute_test').attributes) == 2
        self.validator.error_on_missing_attribute = True
        with self.assertRaises(AssertionError):
            self.validator.resources('azurerm_virtual_machine').attribute('tags').attribute('garbage')
        self.validator.error_on_missing_attribute = False

    def test_attribute_should_equal(self):
        self.assertIsNone(self.validator.resources('azurerm_virtual_machine').attribute('not_matching').should_equal('true'))
        with self.assertRaises(AssertionError):
            self.validator.resources('azurerm_virtual_machine').attribute('not_matching').should_equal('false')

    def test_attribute_should_not_equal(self):
        self.assertIsNone(self.validator.resources('azurerm_virtual_machine').attribute('not_matching').should_not_equal('false'))
        with self.assertRaises(AssertionError):
            self.validator.resources('azurerm_virtual_machine').attribute('not_matching').should_not_equal('true')

    def test_attribute_should_have_attributes(self):
        self.assertIsNone(self.validator.resources('azurerm_virtual_machine').attribute('tags').should_have_attributes('name'))
        with self.assertRaises(AssertionError):
            self.validator.resources('azurerm_virtual_machine').attribute('tags').should_have_attributes('names')

    def test_attribute_should_not_have_attributes(self):
        self.assertIsNone(self.validator.resources('azurerm_virtual_machine').attribute('tags').should_not_have_attributes('names'))
        with self.assertRaises(AssertionError):
            self.validator.resources('azurerm_virtual_machine').attribute('tags').should_not_have_attributes('name')

    def test_attribute_should_match_regex(self):
        self.assertIsNone(self.validator.resources('resource_with_count').attribute('ami').should_match_regex('ami-.*'))
        with self.assertRaises(AssertionError):
            self.validator.resources('resource_with_count').attribute('ami').should_match_regex('garbage-.*')
        with self.assertRaises(AssertionError):
            self.validator.resources('resource_with_count').attribute('tags').should_match_regex('garbage-.*')

    def test_attribute_should_be_json(self):
        self.assertIsNone(self.validator.resources('azurerm_virtual_machine').attribute('valid_json').should_be_valid_json())
        with self.assertRaises(AssertionError):
            self.validator.resources('azurerm_virtual_machine').attribute('tags').should_be_valid_json()

    def test_variable_exists(self):
        self.assertIsNone(self.validator.variable('image-aws-rhel74').value_exists())
        with self.assertRaises(AssertionError):
            self.validator.variable('image-aws-blah').value_exists()

    def test_variable_value_equals(self):
        self.assertIsNone(self.validator.variable('image-aws-rhel74').value_equals('ami-bb9a6bc2'))
        with self.assertRaises(AssertionError):
            self.validator.variable('image-aws-rhel74').value_equals('ami-blah')

    def test_variable_value_matches_regex(self):
        self.assertIsNone(self.validator.variable('image-aws-rhel74').value_matches_regex('ami-.*'))
        with self.assertRaises(AssertionError):
            self.validator.variable('image-aws-rhel74').value_matches_regex('ami-blah.*')
