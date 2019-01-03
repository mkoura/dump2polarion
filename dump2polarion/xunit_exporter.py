# -*- coding: utf-8 -*-
# pylint: disable-all

import warnings

from dump2polarion.exporters.xunit_exporter import *  # noqa

warnings.warn(
    "The xunit_exporter module was moved to 'dump2polarion.exporters.xunit_exporter'",
    DeprecationWarning,
)
