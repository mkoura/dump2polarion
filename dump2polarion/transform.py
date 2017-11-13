# -*- coding: utf-8 -*-
"""
Functions for validating and transforming results. These are specific for given Polarion project.

If the 'polarion-lookup-method' is set to 'custom', this is the place where you can
set the 'id' of the testcase to desired value.
"""

from __future__ import unicode_literals, absolute_import

import re

from dump2polarion.verdicts import Verdicts


def only_passed_and_wait(result):
    """Returns PASS and WAIT results only, skips everything else."""
    verdict = result.get('verdict', '').strip().lower()
    if verdict in Verdicts.PASS + Verdicts.WAIT:
        return result


# pylint: disable=unused-argument
def get_results_transform_cfme(config):
    """Return result transformation function for CFME."""
    cfme_searches = [
        'Skipping due to these blockers',
        'SKIPME:',
        'BZ ?[0-9]+',
        'GH ?#?[0-9]+',
        'GH#ManageIQ',
    ]
    cfme_skips = re.compile('(' + ')|('.join(cfme_searches) + ')')

    def results_transform_cfme(result):
        """Results transform for CFME."""
        # make sure that last part of classname is included in "title", e.g.
        # "TestServiceRESTAPI.test_power_parent_service"
        classname = result.get('classname', '')
        if classname:
            filepath = result.get('file', '')
            title = result.get('title')
            if title and '/' in filepath and '.' in classname:
                fname = filepath.split('/')[-1].replace('.py', '')
                last_classname = classname.split('.')[-1]
                # last part of classname is not file name
                if fname != last_classname and last_classname not in title:
                    result['title'] = '{0}.{1}'.format(last_classname, title)
            # we don't need to pass classnames?
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
