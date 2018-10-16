=====
Usage
=====


To develop on terraformtestinglib:

.. code-block:: bash

    # The following commands require pipenv as a dependency

    # To lint the project
    _CI/scripts/lint

    # To execute the testing
    _CI/scripts/test

    # To create a graph of the package and dependency tree
    _CI/scripts/graph

    # To build a package of the project under the directory "dist/"
    _CI/scripts/build

    # To see the package version
    _CI/scipts/tag

    # To bump semantic versioning [major|minor|patch]
    _CI/scipts/tag --major|--minor|--patch

    # To upload the project to a pypi repo if user and password is properly provided
    _CI/scripts/upload

    # To build the documentation of the project
    _CI/scripts/document



To use terraformtestinglib in a project for linting:

.. code-block:: python

    from terraformtestinglib import Stack
    stack = Stack('path_to_tf_files',
                  'path_to_naming_yaml',
                  'optional_path_to_positioning_yaml',
                  'optional_path_to_global.tfvars)
    stack.validate()
    for error in stack.errors:
        print(error)


.. code-block:: bash

    # naming.yaml should follow the following schema
    #
    # Schema([{'resource': basestring,
    #          'regex': is_valid_regex,
    #         Optional('fields'): [{'value': basestring,
    #                               'regex': is_valid_regex}]}])
    #
    # Example

    ---

    - resource: terraform_resource_name
      regex: .* # regex to lint terraform id
      fields:
        - value: tags.Name
          regex: ^cust[dtaps](?:ew1)-pc[0-9]{2}$  # regex to lint the name of the tag
        - value: tags.Other
          regex: ^cust[dtaps](?:ew1)-other[0-9]{2}$  # regex to lint the name of the tag


.. code-block:: bash

    # positioning.yaml should follow the following schema
    #
    # Schema({And(basestring, lambda x: x.endswith('.tf')): [basestring]})
    #
    #
    # Example


    _data.tf:
       - terraform
       - data
    _provider.tf:
       - provider
    _variables.tf:
       - variable
    compute.tf:
       - azurerm_app_service
       - azurerm_app_service_plan
       - azurerm_virtual_machine
       - aws_instance

