# -*- coding: utf-8 -*-
"""
Helper functions for handling data in sqlite3.
"""

from __future__ import unicode_literals

import os

import sqlite3
from sqlite3 import Error

from collections import OrderedDict

from . import ImportedData, Dump2PolarionException


def get_testrun_from_sqlite(conn):
    """Returns testrun id saved from original csv file."""
    cur = conn.cursor()
    try:
        cur.execute('SELECT testrun FROM testrun')
        return cur.fetchone()[0]
    except (IndexError, Error):
        return


def open_sqlite(db_file):
    """Opens database connection."""
    db_file = os.path.expanduser(db_file)
    with open(db_file):
        # test that file can be accessed
        pass
    try:
        return sqlite3.connect(db_file)
    except Error as err:
        raise Dump2PolarionException('{}'.format(err))


def import_sqlite(db_file):
    """Reads the content of the database file and returns imported data."""
    conn = open_sqlite(db_file)
    cur = conn.cursor()
    # get all rows that were not exported yet
    cur.execute("SELECT * FROM testcases WHERE exported != 'yes'")
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


def mark_exported_sqlite(db_file):
    """Marks all rows with verdict as exported."""
    conn = open_sqlite(db_file)
    cur = conn.cursor()
    cur.execute(
        "UPDATE testcases SET exported = 'yes' WHERE verdict is not null and verdict != ''")
    conn.commit()
    conn.close()
