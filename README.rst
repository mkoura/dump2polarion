dump2polarion
=============
.. image:: https://travis-ci.org/mkoura/dump2polarion.svg?branch=master
    :target: https://travis-ci.org/mkoura/dump2polarion

Usage
-----
Automatic submission out of the CSV or SQLite input file to Polarion® XUnit Importer:

.. code-block::

    polarion_dumper.py -i {input_file}

You need to set the following environment variables (the same are used for pylarion):

.. code-block::

    export POLARION_USERNAME=kerberos_username
    export POLARION_PASSWORD=kerberos_password

Or you can specify credentials on command line with ``--user kerberos_username --password kerberos_password``.  
Or you can specify credentials in ``dump2polarion.yaml`` file. Lookup path is current directory and ``~/.config``. You can also specify the config file on command line with ``-c config_file.yaml``.

By default test results are submitted to Polarion®. You can disable this bahavior with ``-n`` option. In this case the XML file used for results submission will be saved to disk. Default file location is current directory, default file name is `testrun_TESTRUN_ID-TIMESTAMP.xml` (can be overriden with ``-o`` option).

When output file is specified with ``-o PATH``, the XML file used for results submission will be saved to disk. If `PATH` is a directory, resulting file will be `PATH/testrun_TESTRUN_ID-TIMESTAMP.xml`.

When the input file is XML, it is expected that it's XML file with results (e.g. saved earlier with ``-o FILE -n``) and it is submitted to Polarion®.

Install
-------
You don't need to install the package, you can use the scripts directly from the cloned repository.

To install the package to your virtualenv, run

.. code-block::

    pip install dump2polarion

or install it from cloned directory

.. code-block::

    pip install .

Package on PyPI <https://pypi.python.org/pypi/dump2polarion>

Requirements
------------
You need ``sqlite3``, all recent python versions include it by default. The rest is listed in ``requirements.txt``.

CSV format
----------
There needs to be a row with field names - it is by default when exported from Polarion®.

Fields are ID; Title; Test Case ID (optional but recommended); Verdict; Comment (optional); Time (optional); stdout (optional); stderr (optional) + any other field you want. Order of the fields and case doesn't matter.

The "Verdict" field and any optional fields must be added manually. Valid values for "verdict" are "passed", "failed", "skipped", "waiting" or empty. It's case insensitive.

There can be any content before the row with field names and the test results.

SQLite format
-------------
You can convert the CSV file exported out of Polarion® using the ``csv2sqlite.py`` script:

.. code-block::

    csv2sqlite.py -i {input_file.csv} -o {output_file.sqlite3}

How to submit the XML file manually
-----------------------------------

.. code-block::

    polarion_dumper.py -i output.xml --user {user} --password {password}

or

.. code-block::

    curl -k -u {user}:{password} -X POST -F file=@./output.xml https://polarion.engineering.redhat.com/polarion/import/xunit

More info
---------
For CFME QE specific instructions see <https://mojo.redhat.com/docs/DOC-1098563>

For info about XUnit Importer see <https://mojo.redhat.com/docs/DOC-1073077>
