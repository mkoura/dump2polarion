# -*- coding: utf-8 -*-
"""
Helper functions for handling data in sqlite3.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os
import sqlite3
from collections import OrderedDict

from dump2polarion import xunit_exporter
from dump2polarion.exceptions import Dump2PolarionException

# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


SQLITE_EXT = (".sqlite", ".sqlite3", ".db", ".db3")


def _get_testrun_from_sqlite(conn):
    """Returns testrun id saved from original csv file."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT testrun FROM testrun")
        return cur.fetchone()[0]
    except (IndexError, sqlite3.Error):
        return None


def _open_sqlite(db_file):
    """Opens database connection."""
    db_file = os.path.expanduser(db_file)
    try:
        with open(db_file):
            # test that the file can be accessed
            pass
        return sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
    except (IOError, sqlite3.Error) as err:
        raise Dump2PolarionException("{}".format(err))


# pylint: disable=unused-argument
def import_sqlite(db_file, older_than=None, **kwargs):
    """Reads the content of the database file and returns imported data."""
    conn = _open_sqlite(db_file)
    cur = conn.cursor()
    # get rows that were not exported yet
    select = "SELECT * FROM testcases WHERE exported != 'yes'"
    if older_than:
        cur.execute(" ".join((select, "AND sqltime < ?")), (older_than,))
    else:
        cur.execute(select)
    columns = [description[0] for description in cur.description]
    rows = cur.fetchall()

    # map data to columns
    results = []
    for row in rows:
        record = OrderedDict(list(zip(columns, row)))
        results.append(record)

    testrun = _get_testrun_from_sqlite(conn)

    conn.close()

    return xunit_exporter.ImportedData(results=results, testrun=testrun)


def mark_exported_sqlite(db_file, older_than=None):
    """Marks rows with verdict as exported."""
    logger.debug("Marking rows in database as exported")
    conn = _open_sqlite(db_file)
    cur = conn.cursor()
    update = "UPDATE testcases SET exported = 'yes' WHERE verdict IS NOT null AND verdict != ''"
    if older_than:
        cur.execute(" ".join((update, "AND sqltime < ?")), (older_than,))
    else:
        cur.execute(update)
    conn.commit()
    conn.close()
