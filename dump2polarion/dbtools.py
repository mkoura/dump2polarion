# -*- coding: utf-8 -*-
"""
Helper functions for handling data in sqlite3.
"""

from __future__ import unicode_literals, absolute_import

import os

import logging
import sqlite3
from sqlite3 import Error as SQLiteError

from collections import OrderedDict

from dump2polarion import ImportedData
from dump2polarion.exceptions import Dump2PolarionException


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


def get_testrun_from_sqlite(conn):
    """Returns testrun id saved from original csv file."""
    cur = conn.cursor()
    try:
        cur.execute('SELECT testrun FROM testrun')
        return cur.fetchone()[0]
    except (IndexError, SQLiteError):
        return


def open_sqlite(db_file):
    """Opens database connection."""
    db_file = os.path.expanduser(db_file)
    with open(db_file):
        # test that the file can be accessed
        pass
    try:
        return sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
    except SQLiteError as err:
        raise Dump2PolarionException('{}'.format(err))


# pylint: disable=unused-argument
def import_sqlite(db_file, older_than=None, **kwargs):
    """Reads the content of the database file and returns imported data."""
    conn = open_sqlite(db_file)
    cur = conn.cursor()
    # get rows that were not exported yet
    select = "SELECT * FROM testcases WHERE exported != 'yes'"
    if older_than:
        cur.execute(' '.join((select, "AND sqltime < ?")), (older_than, ))
    else:
        cur.execute(select)
    columns = [description[0] for description in cur.description]
    rows = cur.fetchall()

    # map data to columns
    results = []
    for row in rows:
        record = OrderedDict(zip(columns, row))
        results.append(record)

    testrun = get_testrun_from_sqlite(conn)

    conn.close()

    return ImportedData(results=results, testrun=testrun)


def mark_exported_sqlite(db_file, older_than=None):
    """Marks rows with verdict as exported."""
    logger.debug("Marking rows in database as exported")
    conn = open_sqlite(db_file)
    cur = conn.cursor()
    update = "UPDATE testcases SET exported = 'yes' WHERE verdict IS NOT null AND verdict != ''"
    if older_than:
        cur.execute(' '.join((update, "AND sqltime < ?")), (older_than, ))
    else:
        cur.execute(update)
    conn.commit()
    conn.close()
