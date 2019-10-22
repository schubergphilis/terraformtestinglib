#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File: testing.py
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
Main code for testing.

.. _Google Python Style Guide:
   http://google.github.io/styleguide/pyguide.html

"""

import functools
import json
import logging
import re
import typing
from operator import attrgetter
from dataclasses import dataclass


from terraformtestinglib.terraformtestinglib import Parser

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
LOGGER_BASENAME = '''testing'''
LOGGER = logging.getLogger(LOGGER_BASENAME)
LOGGER.addHandler(logging.NullHandler())


def assert_on_error(func):
    """Raises assertion error exceptions if the wrapped method returned any errors."""
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        """Wrapped method."""
        value, errors = func(*args, **kwargs)
        if errors:
            raise AssertionError('\n\t' + '\n\t'.join(sorted(errors)))
        return value

    return wrapped


@dataclass
class Entity:
    """Basic model of an entity exposing required attributes."""

    type: str
    name: str
    data: typing.Any


@dataclass
class Resource(Entity):
    """Basic model of a resource exposing required attributes."""


@dataclass
class Data(Entity):
    """Basic model of a data object exposing required attributes."""


@dataclass
class Provider(Entity):
    """Basic model of a provider object exposing required attributes."""


@dataclass
class Terraform(Entity):
    """Basic model of a provider object exposing required attributes."""


class Validator(Parser):
    """Object exposing resources and variables of terraform plans."""

    def __init__(self,
                 configuration_path,
                 global_variables_file_path=None,
                 raise_on_missing_variable=True,
                 environment_variables=None):
        super(Validator, self).__init__(configuration_path,
                                        global_variables_file_path,
                                        raise_on_missing_variable,
                                        environment_variables)
        self._logger = logging.getLogger(f'{LOGGER_BASENAME}.{self.__class__.__name__}')
        self.error_on_missing_attribute = False

    def resources(self, type_):
        """Filters resources based on resource type which is always cast to list.

        Args:
            type_ (basestring|list): The type of resources to filter on. Always gets cast to a list.

        Returns:
            ResourceList : An object containing the resources matching the type provided

        """
        resource_types = self.to_list(type_)
        resources = []
        for resource_type, resource in self.hcl_view.resources.items():
            if resource_type in resource_types:
                for resource_name, resource_data in resource.items():
                    if resource_data.get('tags', {}).get('skip-testing'):
                        self._logger.warning('Skipping resource %s testing '
                                             'due to user overriding tag.', resource_name)
                    else:
                        resources.append(Resource(resource_type, resource_name, resource_data))
        return ResourceList(self, sorted(resources, key=attrgetter('name')))

    def data(self, type_):
        """Filters data based on data type which is always cast to list.

        Args:
            type_ (basestring|list): The type of data attributes to filter on. Always gets cast to a list.

        Returns:
            DataList : An object containing the data matching the type provided

        """
        return self._entity('data', Data, DataList, type_)

    def provider(self, type_):
        """Filters providers based on provider type which is always cast to list.

        Args:
            type_ (basestring|list): The type of provider to filter on. Always gets cast to a list.

        Returns:
            ProviderList : An object containing the providers matching the type provided

        """
        return self._entity('provider', Provider, ProviderList, type_)

    def terraform(self, type_):
        """Filters terraform entries based on provided type which is always cast to list.

        Args:
            type_ (basestring|list): The type of terraform attributes to filter on. Always gets cast to a list.

        Returns:
            TerraformList : An object containing the terraform objects matching the type provided

        """
        return self._entity('terraform', Terraform, TerraformList, type_)

    def _entity(self, state_object, entity_object, entity_container, entity_type):
        types = self.to_list(entity_type)
        output_list = []
        for _type, data in getattr(self.hcl_view, state_object).items():
            if _type in types:
                output_list.append(entity_object(_type, _type, data))
        return entity_container(self, sorted(output_list, key=attrgetter('name')))

    def variable(self, name):
        """Returns a variable object of the provided name.

        Args:
            name (basestring): The name of the variable to retrieve

        Returns:
            Variable : An object modeling a variable

        """
        return Variable(name, self.hcl_view.state.get('variable', {}).get(name))

    def get_variable_value(self, variable):
        """Retrieves the variable value from the global view state.

        Args:
            variable (basestring): The variable to retrieve the value for

        Returns:
            value : The value of the retrieved variable

        """
        return self.hcl_view.get_variable_value(variable)

    @staticmethod
    def to_list(value):
        """Casts to list the provided argument if not a list already.

        Args:
            value (basestring|list): Casts the provided value to list if not already

        Returns:
            value (list) : A list of the value or values

        """
        if not isinstance(value, (tuple, list)):
            value = [value]
        return value


class Container:
    """An object handling the exposing of attributes of different resources of terraform."""

    def __init__(self, validator_instance, entities):
        self._logger = logging.getLogger(f'{LOGGER_BASENAME}.{self.__class__.__name__}')
        self.validator = validator_instance
        self.__entities = entities

    @property
    def _entities(self):
        return self.__entities

    @assert_on_error
    def attribute(self, name):
        """Filters attributes based on the provided name.

        Args:
            name (basestring): The name to match against

        Raises:
            AssertionError : If any errors are calculated

        Returns:
            AttributeList (list) : An object containing any attributes matching the check

        """
        errors = []
        attributes_list = []
        for entity in self._entities:
            if not isinstance(entity.data, dict):
                attributes_list.append(Attribute(entity, name, entity.data))
                continue
            if name in entity.data.keys():
                if isinstance(entity.data.get(name), list):
                    for entry in entity.data.get(name):
                        attributes_list.append(Attribute(entity, name, entry))
                else:
                    attributes_list.append(Attribute(entity, name, entity.data.get(name)))
            elif self.validator.error_on_missing_attribute:
                errors.append(f"[{entity.type}.{entity.name}] should have attribute: '{name}'")
        return AttributeList(self.validator, attributes_list), errors

    @assert_on_error
    def attribute_matching_regex(self, regex):
        """Filters attributes based on the provided regex.

        Args:
            regex (basestring): A basestring of a valid regular expression to match against

        Raises:
            AssertionError : If any errors are calculated

        Returns:
            AttributeList (list) : An object containing any attributes matching the check

        """
        errors = []
        attributes_list = []
        for resource in self._entities:
            matched = False
            for attribute in resource.data.keys():
                if re.search(regex, attribute):
                    attributes_list.append(Attribute(resource,
                                                     attribute,
                                                     resource.data.get(attribute)))
                    matched = True
            if self.validator.error_on_missing_attribute and not matched:
                errors.append(f"[{resource.type}.{resource.name}] should have attribute matching regex: '{regex}'")
        return AttributeList(self.validator, attributes_list), errors

    @assert_on_error
    def should_have_attributes(self, attributes_list):
        """Validates that the resource has the provided arguments which are always cast to a list.

        Args:
            attributes_list (list): A list of strings for attributes to check against

        Raises:
            AssertionError : If any errors are calculated

        Returns:
            None

        """
        attributes_list = self.validator.to_list(attributes_list)
        errors = []
        for resource in self._entities:
            for attribute in attributes_list:
                if attribute not in resource.data.keys():
                    errors.append(f"[{resource.type}.{resource.name}] should have attribute: '{attribute}'")
        return None, errors

    @assert_on_error
    def should_not_have_attributes(self, attributes_list):
        """Validates that the resource does not have the provided arguments which are always cast to a list.

        Args:
            attributes_list (list): A list of strings for attributes to check against

        Raises:
            AssertionError : If any errors are calculated

        Returns:
            None

        """
        attributes_list = self.validator.to_list(attributes_list)
        errors = []
        for resource in self._entities:
            for attribute in attributes_list:
                if attribute in resource.data.keys():
                    errors.append(f"[{resource.type}.{resource.name}] should not have attribute(s): '{attribute}'")
        return None, errors

    def if_has_attribute(self, attribute):
        """Filters the entities based on the provided attribute.

        Args:
            attribute (basestring): The attribute to filter the resources on

        Returns:
             (list) : An entities list object with all resources following the pattern

        """
        entities = []
        for entity in self._entities:
            if attribute in entity.data.keys():
                entities.append(entity)
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_not_has_attribute(self, attribute):
        """Filters the entities based on the non existence of the provided attribute.

        Args:
            attribute (basestring): The attribute to filter the resources on

        Returns:
            (list)) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            if attribute not in entity.data.keys():
                entities.append(entity)
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_has_attribute_with_value(self, attribute, value):
        """Filters the entities based on the provided attribute and value.

        Args:
            attribute (basestring): The attribute to filter the entities on
            value : The value to match with

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            if attribute in entity.data.keys():
                attribute_value = entity.data.get(attribute)
                if attribute_value == value:
                    entities.append(entity)
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_not_has_attribute_with_value(self, attribute, value):
        """Filters the entities based on the provided attribute and value.

        Args:
            attribute (basestring): The attribute to filter the resources on
            value : The value to not match

        Returns:
            (list)) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            if attribute in entity.data.keys():
                attribute_value = entity.data.get(attribute)
                if not attribute_value == value:
                    entities.append(entity)
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_has_attribute_with_regex_value(self, attribute, regex):
        """Filters the entities based on the provided attribute and value.

        Args:
            attribute (basestring): The attribute to filter the entities on if the value matches the regex provided
            regex : The regex to match with

        Returns:
            (list)) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            if attribute in entity.data.keys():
                attribute_value = entity.data.get(attribute)
                try:
                    if re.search(regex, attribute_value):
                        entities.append(entity)
                except TypeError:
                    pass
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_not_has_attribute_with_regex_value(self, attribute, regex):
        """Filters the entities based on the provided attribute and value.

        Args:
            attribute (basestring): The attribute to filter the entities on if the value does not match the regex
            regex : The regex not to match with

        Returns:
            (list)) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            if attribute in entity.data.keys():
                attribute_value = entity.data.get(attribute)
                try:
                    if not re.search(regex, attribute_value):
                        entities.append(entity)
                except TypeError:
                    pass
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_has_subattribute(self, parent_attribute, attribute):
        """Filters the entities based on the provided parent and child attribute.

        Args:
            parent_attribute (basestring): The parent attribute to filter the resources on
            attribute (basestring): The child attribute to filter the entities on if it exists

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            parent = entity.data.get(parent_attribute, {})
            if parent.get(attribute):
                entities.append(entity)
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_not_has_subattribute(self, parent_attribute, attribute):
        """Filters the entities based on the provided parent and child attribute.

        Args:
            parent_attribute (basestring): The parent attribute to filter the entities on
            attribute (basestring): The child attribute to filter the entities on if it does not exists

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            parent = entity.data.get(parent_attribute, {})
            if not parent.get(attribute):
                entities.append(entity)
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_has_subattribute_with_value(self, parent_attribute, attribute, value):
        """Filters the entities based on the provided parent and child attribute and value.

        Args:
            parent_attribute (basestring): The parent attribute to filter the entities on
            attribute (basestring): The child attribute to filter the entities on
            value : The value to match with for the child attribute

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            parent = entity.data.get(parent_attribute, {})
            try:
                if value == parent.get(attribute):
                    entities.append(entity)
            except TypeError:
                pass
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_not_has_subattribute_with_value(self, parent_attribute, attribute, value):
        """Filters the entities based on the provided parent and child attribute and value.

        Args:
            parent_attribute (basestring): The parent attribute to filter the entities on
            attribute (basestring): The child attribute to filter the entities on
            value : The value to not match with for the child attribute

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            parent = entity.data.get(parent_attribute, {})
            try:
                if not value == parent.get(attribute):
                    entities.append(entity)
            except TypeError:
                pass
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_has_subattribute_with_regex_value(self, parent_attribute, attribute, regex):
        """Filters the entities based on the provided parent and child attribute and regex for value matching.

        Args:
            parent_attribute (basestring): The parent attribute to filter the entities on
            attribute (basestring): The child attribute to filter the entities on
            regex : The regex to match with for the child attribute's value

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            parent = entity.data.get(parent_attribute, {})
            try:
                if re.search(regex, parent.get(attribute)):
                    entities.append(entity)
            except TypeError:
                pass
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))

    def if_not_has_subattribute_with_regex_value(self, parent_attribute, attribute, regex):
        """Filters the entities based on the provided parent and child attribute and regex for value matching.

        Args:
            parent_attribute (basestring): The parent attribute to filter the entities on
            attribute (basestring): The child attribute to filter the entities on
            regex : The regex to not match with for the child attribute's value

        Returns:
            (list) : An entities list object with all entities following the pattern

        """
        entities = []
        for entity in self._entities:
            parent = entity.data.get(parent_attribute, {})
            try:
                if not re.search(regex, parent.get(attribute)):
                    entities.append(entity)
            except TypeError:
                pass
        return self.__class__(self.validator, sorted(entities, key=attrgetter('name')))


class DataList(Container):
    """A list of data objects being capable to filter on specific requirements."""


class ProviderList(Container):
    """A list of provider objects being capable to filter on specific requirements."""


class TerraformList(Container):
    """A list of terraform objects being capable to filter on specific requirements."""


class ResourceList(Container):
    """A list of resource objects being capable to filter on specific requirements."""

    def resources(self, type_):
        """Filters resources based on resource type which is always cast to list.

        Args:
            type_ (list|basestring): The type of resources to filter on. Always gets cast to list.

        Raises:
            AssertionError : If any errors are calculated

        Returns:
            ResourceList (list) : An object containing any resources matching the type

        """
        resource_types = self.validator.to_list(type_)
        resources = []
        for resource in self._entities:
            if resource.type in resource_types:
                resources.append(resource)
        return ResourceList(self.validator, sorted(resources, key=attrgetter('name')))


class AttributeList:
    """Object containing attribute objects and providing validation methods for them."""

    def __init__(self, validator, attributes):
        self._logger = logging.getLogger(f'{LOGGER_BASENAME}.{self.__class__.__name__}')
        self.validator = validator
        self.attributes = attributes

    @assert_on_error
    def attribute(self, name):
        """Filters attributes on matching the provided name.

        Args:
            name ( basestring): The name to match the attribute with

        Returns:
            AttributeList : A container of attribute objects

        """
        errors = []
        attributes = []
        for attribute in self.attributes:
            if isinstance(attribute.value, list):
                for entry in attribute.value:
                    attributes.append(Attribute(attribute._resource, f'{attribute.name}.{name}', entry))  # pylint: disable=protected-access
            else:
                if name in attribute.value.keys():
                    attributes.append(Attribute(attribute._resource, f'{attribute.name}.{name}', attribute.value[name]))  # pylint: disable=protected-access
                elif self.validator.error_on_missing_attribute:
                    errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                                  f"should have attribute: '{attribute.name}'")
        return AttributeList(self.validator, attributes), errors

    @assert_on_error
    def should_equal(self, value):
        """Checks for equality for the provided value from all contained attributes.

        Args:
            value : The value to match with

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        for attribute in self.attributes:
            if not attribute.value == value:
                errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                              f"should be '{value}'. Is: '{attribute.value}'")
        return None, errors

    def if_has_attribute_with_value(self, attribute, value):
        """Filters the AttributeList based on the provided attribute and value.

        Args:
            attribute: The attribute to filter on
            value: the value of the attribute to filter on

        Returns:
            AttributeList : A container of attribute objects

        """
        attributes = []
        for attribute_ in self.attributes:
            try:
                if value == attribute_.value.get(attribute):
                    attributes.append(attribute_)
            except TypeError:
                pass
        return AttributeList(self.validator, attributes)

    def if_not_has_attribute_with_value(self, attribute, value):
        """Filters the AttributeList based on the provided attribute and value.

        Args:
            attribute: The attribute to filter on
            value: the value of the attribute to filter on

        Returns:
            AttributeList : A container of attribute objects

        """
        attributes = []
        for attribute_ in self.attributes:
            try:
                if not value == attribute_.value.get(attribute):
                    attributes.append(attribute_)
            except TypeError:
                pass
        return AttributeList(self.validator, attributes)

    @assert_on_error
    def should_not_equal(self, value):
        """Checks for inequality for the provided value from all contained attributes.

        Args:
            value : The value to not match with

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        for attribute in self.attributes:
            if attribute.value == value:
                errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                              f"should not be '{value}'. Is: '{attribute.value}'")
        return None, errors

    @assert_on_error
    def should_have_attributes(self, attributes):
        """Checks for existence for the provided attribute from all contained attributes.

        Args:
            attributes : An attribute or list of attributes to check for

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        for attribute in self.attributes:
            for provided_attribute in self.validator.to_list(attributes):
                if provided_attribute not in attribute.value.keys():
                    errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                                  f"should have attribute: '{provided_attribute}'")
        return None, errors

    @assert_on_error
    def should_not_have_attributes(self, attributes):
        """Checks for lack for the provided attribute from all contained attributes.

        Args:
            attributes : An attribute or list of attributes to check for

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        attributes = self.validator.to_list(attributes)
        for attribute in self.attributes:
            for required_property_name in attributes:
                if required_property_name in attribute.value.keys():
                    errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                                  f"should not have attribute: '{required_property_name}'")
        return None, errors

    @assert_on_error
    def should_match_regex(self, regex):
        """Checks for regular expression match from all contained attributes.

        Args:
            regex (basestring) : A regular expression to match with

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        for attribute in self.attributes:
            try:
                if not re.search(regex, attribute.value):
                    errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                                  f"with value '{attribute.value}' should match regex '{regex}'")
            except (ValueError, TypeError, AttributeError):
                errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                              f"with value '{attribute.value}' should match regex '{regex}'")
        return None, errors

    @assert_on_error
    def should_not_match_regex(self, regex):
        """Checks for regular expression not matching from all contained attributes.

        Args:
            regex (basestring) : A regular expression to not match with

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        for attribute in self.attributes:
            if re.search(regex, attribute.value):
                errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                              f"with value '{attribute.value}' should not match regex '{regex}'")
        return None, errors

    @assert_on_error
    def should_be_valid_json(self):
        """Checks whether the value for the attribute is valid json.

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        errors = []
        for attribute in self.attributes:
            try:
                json.loads(attribute.value)
            except (ValueError, TypeError, AttributeError):
                errors.append(f"[{attribute.resource_type}.{attribute.resource_name}.{attribute.name}] "
                              f"is not valid json")
        return None, errors


class Variable:
    """Models a variable and exposes basic test for it."""

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def value_exists(self):
        """Checks that the value exists.

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        if not self.value:
            raise AssertionError(f"Variable '{self.name}' should have a default value")

    def value_equals(self, value):
        """Checks that the value equals the provided value.

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        if not self.value == value:
            raise AssertionError(f"Variable '{self.name}' should have a default value of {value}. Is: {self.value}")

    def value_matches_regex(self, regex):
        """Checks that the value matches the provided regex.

        Raises:
            AssertionError : If any errors are found on the check

        Returns:
            None

        """
        if not re.search(regex, self.value):
            raise AssertionError(f"Variable '{self.name}' value should match regex '{regex}'. Is: {self.value}")


class Attribute:
    """Models the attribute."""

    def __init__(self, resource, name, value):
        self._resource = resource
        self.name = name
        self.value = value

    @property
    def resource_type(self):
        """Exposes the type of the parent resource object.

        Returns:
            type (basestring): The type of the parent resource

        """
        return self._resource.type

    @property
    def resource_name(self):
        """Exposes the name of the parent resource object.

        Returns:
            name (basestring): The name of the parent resource

        """
        return self._resource.name
