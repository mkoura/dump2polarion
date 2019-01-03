# -*- coding: utf-8 -*-
# pylint: disable-all

import warnings

from dump2polarion.exporters.requirements_exporter import *  # noqa

warnings.warn(
    "The requirements_exporter module was moved to 'dump2polarion.exporters.requirements_exporter'",
    DeprecationWarning,
)
