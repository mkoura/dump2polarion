# -*- coding: utf-8 -*-
# pylint: disable-all

import warnings

from dump2polarion.exporters.transform import *  # noqa

warnings.warn(
    "The transform module was moved to 'dump2polarion.exporters.transform'", DeprecationWarning
)
