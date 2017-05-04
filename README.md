dump2polarion
=

Usage
-
Automatic submission out of the CSV or SQLite input file:
```
./polarion_dumper.py -i {input_file} -t {testrun_id}
```

You need to set the following environment variables (the same are used for pylarion):
```
export POLARION_USERNAME=kerberos_username
export POLARION_PASSWORD=kerberos_password
```
Or you can specify credentials on command line with ``--user kerberos_username --password kerberos_password``.  
Or you can specify credentials in ``dump2polarion.yaml`` file. Lookup path is current directory and ``~/.config``. You can also specify the config file on command line with ``-c config_file.yaml``.

By default test results are submitted to Polarion. You can disable this bahavior with ``-n`` option. In this case the XML file used for results submission will be saved to disk. Default file location is current directory, default file name is `testrun_TESTRUN_ID-TIMESTAMP.xml` (can be overriden with ``-o`` option).

When output file is specified with ``-o PATH``, the XML file used for results submission will be saved to disk. If `PATH` is a directory, resulting file will be `PATH/testrun_TESTRUN_ID-TIMESTAMP.xml`.

Requirements
-
You need ``sqlite3``, it's better to have it installed using the distribution package. The rest is listed in ``requirements.txt``.

CSV format
-
ID, Verdict (one of "passed", "failed", "skipped", "waiting" or empty), Title (optional), Comment (optional), Time (optional), stdout (optional), stderr (optional) + any other field you want, order doesn't matter.

You can export the CSV file out of Polarion, just make sure the ID field is there. The "Verdict" field and any optional fields must be added manually.

SQLite format
-
You can convert the CSV file exported out of Polarion using the ``csv2sqlite.py`` script:
```
./csv2sqlite.py -i {input_file.csv} -o {output_file.sqlite3}
```

How to submit the XML file manually
-
```
curl -k -u {user}:{password} -X POST -F file=@./output.xml https://polarion.engineering.redhat.com/polarion/import/xunit
```

More info
-
<https://mojo.redhat.com/docs/DOC-1073077>
