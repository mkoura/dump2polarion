# -*- coding: utf-8 -*-
"""
Functions for validating and transforming results. These are specific for given Polarion® project.
"""

from __future__ import unicode_literals, absolute_import

import re

from dump2polarion.verdicts import Verdicts


def get_results_transform(project):
    """Returns results transformation function.

    This allows customizations of results data according to requirements
    of the specific project.

    When no results data are returned, this result will be ignored
    and will not be written to the resulting XML.
    """
    cfme_searches = [
        'Skipping due to these blockers',
        'BZ ?[0-9]+',
        'GH ?#?[0-9]+',
        'GH#ManageIQ',
    ]
    cfme_skips = '(' + ')|('.join(cfme_searches) + ')'

    def results_transform_cfme(result):
        """Result checks for CFME."""
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
            if comment and re.search(cfme_skips, comment):
                # found reason for skip
                return result

    if project == 'RHCF3':
        return results_transform_cfme
