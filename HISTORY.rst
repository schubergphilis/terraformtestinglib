.. :changelog:

History
-------

0.1.0 (24-05-2018)
------------------

* First release


1.0.0 (16-10-2018)
------------------

* Implemented variable, count attribute and format method interpolation on both linting and testing capabilities
* Implemented testing capabilities with conditional filtering for resources
* Ported the pipeline portion to python 3.7
* Dropped official support for python2.7


1.0.3 (17-10-2018)
------------------

* Implemented interactive setting of the changelog in HISTORY.rst file on tagging


1.0.4 (25-10-2018)
------------------

* Updated template and dependencies


1.1.0 (07-01-2019)
------------------

* Added support for attributes with same name and filtering attributes on value


1.1.1 (14-01-2019)
------------------

* Correctly handle lists in resource data.


1.1.2 (18-01-2019)
------------------

* Casting to string for replacement in case it is a number


1.2.0 (19-01-2019)
------------------

* Added support for "length" method and multi variable strings


1.2.1 (20-01-2019)
------------------

* fixed bug where count was a string breaking the range calculation


1.2.2 (22-01-2019)
------------------

* added support for multiple same keys that end up being handled as a list internally.


1.2.3 (22-01-2019)
------------------

* added capabilities to skip a test based on a "skip-testing" tag on the resource


1.3.0 (06-02-2019)
------------------

* implemented all terraform supported entities like, data, terraform and provider.


1.4.0 (07-02-2019)
------------------

* implemented skipping positioning checking for a disaster_recovery.tf file. Refactored container object to expose filtering.


1.4.1 (07-02-2019)
------------------

* fixed instantiation of Stack object


1.4.2 (22-10-2019)
------------------

* Updated template and bumped dependencies.


1.4.3 (22-10-2019)
------------------

* Fixed yaml deprecation errors and breakage of format method.


1.4.4 (22-05-2020)
------------------

* Bumped depenencies, getting terraform 12 compatibility.


1.4.5 (25-05-2020)
------------------

* bumped dependencies
