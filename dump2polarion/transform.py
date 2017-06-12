# -*- coding: utf-8 -*-
"""
Functions for validating and transforming results. These are specific for given Polarion project.

If the 'polarion-lookup-method' is set to 'custom', this is the place where you can
set the 'id' of the testcase to desired value.
"""

from __future__ import unicode_literals, absolute_import

import re

from dump2polarion.verdicts import Verdicts


# pylint: disable=unused-argument
def get_results_transform_cfme(config):
    """Return result transformation function for CFME."""
    cfme_searches = [
        'Skipping due to these blockers',
        'BZ ?[0-9]+',
        'GH ?#?[0-9]+',
        'GH#ManageIQ',
    ]
    cfme_skips = re.compile('(' + ')|('.join(cfme_searches) + ')')

    def results_transform_cfme(result):
        """Results transform for CFME."""
        if result.get('classname'):
            # we don't need classnames?
            del result['classname']
        verdict = result.get('verdict', '').strip().lower()
        # we want to submit PASS and WAIT results
        if verdict in Verdicts.PASS + Verdicts.WAIT:
            return result
        # ... and SKIP results where there is a good reason (blocker etc.)
        if verdict in Verdicts.SKIP:
            comment = result.get('comment')
            if comment and cfme_skips.search(comment):
                # found reason for skip
                return result

    return results_transform_cfme


PROJECT_MAPPING = {
    'RHCF3': get_results_transform_cfme,
}


def get_results_transform(config):
    """Returns results transformation function.

    The transformation function is returned by calling corresponding "getter" function.

    This allows customizations of results data according to requirements
    of the specific project.

    When no results data are returned, this result will be ignored
    and will not be written to the resulting XML.
    """

    project = config['xunit_import_properties']['polarion-project-id']
    if project in PROJECT_MAPPING:
        return PROJECT_MAPPING[project](config)
