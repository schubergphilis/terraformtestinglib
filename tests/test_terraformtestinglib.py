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

from betamax.fixtures import unittest
from terraformtestinglib import Stack
from terraformtestinglib.terraformtestinglibexceptions import InvalidNaming, InvalidPositioning
from terraformtestinglib.configuration import is_valid_regex
from terraformtestinglib.utils import  ResourceError, FilenameError

__author__ = '''Costas Tyfoxylos <ctyfoxylos@schubergphilis.com>'''
__docformat__ = '''google'''
__date__ = '''2018-05-24'''
__copyright__ = '''Copyright 2018, Costas Tyfoxylos'''
__credits__ = ["Costas Tyfoxylos"]
__license__ = '''MIT'''
__maintainer__ = '''Costas Tyfoxylos'''
__email__ = '''<ctyfoxylos@schubergphilis.com>'''
__status__ = '''Development'''  # "Prototype", "Development", "Production".


class TestTerraformtestinglib(unittest.BetamaxTestCase):

    def setUp(self):
        """
        Test set up

        This is where you can setup things that you use throughout the tests. This method is called before every test.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.fixtures = os.path.join(current_dir, 'fixtures')
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
        self.assertRaises(InvalidNaming, Stack, self.stack_path, 'random/path', self.positioning_file)
        self.assertRaises(InvalidNaming, Stack, self.stack_path, self.broken_schema_naming_file, self.positioning_file)
        self.assertRaises(InvalidNaming, Stack, self.stack_path, self.broken_yaml_naming_file, self.positioning_file)

    def test_positioning_file(self):
        self.assertRaises(InvalidPositioning, Stack, self.stack_path, self.naming_file, 'random/path')
        self.assertRaises(InvalidPositioning, Stack, self.stack_path, self.naming_file, self.broken_schema_positioning_file)
        self.assertRaises(InvalidPositioning, Stack, self.stack_path, self.naming_file, self.broken_yaml_positioning_file)
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
