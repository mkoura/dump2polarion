# -*- coding: utf-8 -*-
# pylint: disable-all

import warnings

from dump2polarion.exporters.testcases_exporter import *  # noqa

warnings.warn(
    "The testcases_exporter module was moved to 'dump2polarion.exporters.testcases_exporter'",
    DeprecationWarning,
)
