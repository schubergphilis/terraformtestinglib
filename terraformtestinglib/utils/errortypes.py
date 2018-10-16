#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: errortypes.py
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
Main code for errortypes

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

from collections import namedtuple
from colored import fore, style

__author__ = '''Costas Tyfoxylos <ctyfoxylos@schubergphilis.com>'''
__docformat__ = '''google'''
__date__ = '''2018-05-24'''
__copyright__ = '''Copyright 2018, Costas Tyfoxylos'''
__credits__ = ["Costas Tyfoxylos"]
__license__ = '''MIT'''
__maintainer__ = '''Costas Tyfoxylos'''
__email__ = '''<ctyfoxylos@schubergphilis.com>'''
__status__ = '''Development'''  # "Prototype", "Development", "Production".


RuleError = namedtuple('RuleError', ['resource_type', 'entity', 'field', 'regex', 'value', 'original_value'])


class ResourceError:  # pylint: disable=too-few-public-methods
    """Models the Resource error and provides a nice printed version"""

    def __init__(self, filename, resource, entity, field, regex, value, original_value):  # pylint: disable=too-many-arguments
        self.filename = filename
        self.resource = resource
        self.entity = entity
        self.field = field
        self.regex = regex
        self.value = value
        self.original_value = original_value

    def __str__(self):
        filename = (
            fore.RED + style.BOLD + self.filename + '/' + self.resource + style.RESET)  # pylint: disable=no-member
        resource = (fore.RED + style.BOLD + self.entity + style.RESET)  # pylint: disable=no-member
        regex = (fore.RED + style.BOLD + self.regex + style.RESET)  # pylint: disable=no-member
        value = (fore.RED + style.BOLD + self.value + style.RESET)  # pylint: disable=no-member
        field = (fore.RED + style.BOLD + self.field + style.RESET)  # pylint: disable=no-member
        text = ('Naming convention not followed on file {filename} for resource '
                '{resource} for field {field}'
                '\n\tRegex not matched : {regex}'
                '\n\tValue             : {value}').format(filename=filename,
                                                          resource=resource,
                                                          regex=regex,
                                                          value=value,
                                                          field=field)
        if self.original_value:
            original = (fore.RED + style.BOLD + self.original_value + style.RESET)  # pylint: disable=no-member
            text += '\n\tOriginal Value    : {original}'.format(original=original)
        return text


class FilenameError:  # pylint: disable=too-few-public-methods
    """Models the Filename error and provides a nice printed version"""

    def __init__(self, filename, resource, target):
        self.filename = filename
        self.resource = resource
        self.target = target

    def __str__(self):
        filename = (
            fore.RED + style.BOLD + self.filename + '/' + self.resource + style.RESET)  # pylint: disable=no-member
        resource = (fore.RED + style.BOLD + self.resource + style.RESET)  # pylint: disable=no-member
        target = (fore.RED + style.BOLD + self.target + style.RESET)  # pylint: disable=no-member
        return ('Filename positioning not followed on file {filename} '
                'for resource {resource}. \n\tShould be in file : {target}.').format(filename=filename,
                                                                                     resource=resource,
                                                                                     target=target)
