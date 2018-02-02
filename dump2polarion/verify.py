# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Verifies that data were updated in Polarion.
"""

from __future__ import absolute_import, unicode_literals

import logging
import os
import time

import requests


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)


class QueueSearch(object):
    """Search for job in the completed jobs queue."""

    _DEFAULT_TIMEOUT = 600
    _DEFAULT_DELAY = 10

    def __init__(self, user, password, queue_url):
        self.user = user
        self.password = password
        self.queue_url = queue_url
        self.last_id = None
        self.skip = False
        self._check_setup()

    def _check_setup(self):
        """Checks that all the data that is needed for submit verification is available."""
        if not self.queue_url:
            logger.error(
                'The queue url is not configured, skipping submit verification')
            self.skip = True
            return

        if not all([self.user, self.password]):
            logger.error('Missing credentials, skipping submit verification')
            self.skip = True
            return

    def download_queue(self, jobs_per_page=50, current_page=1):
        """Downloads data of completed jobs."""
        if self.skip:
            return

        url = '{0}?jobtype=completed&jobsPerPage={1}&currentPage={2}'.format(
            self.queue_url, jobs_per_page, current_page)
        try:
            response = requests.get(
                url,
                auth=(self.user, self.password),
                verify=False,
                headers={'Accept': 'application/json'}
            )
            if response:
                response = response.json()
            else:
                response = None
        # pylint: disable=broad-except
        except Exception as err:
            logger.error(err)
            response = None

        return response

    def find_job(self, job_id, last_id, max_depth=10, _current_page=1):
        """Finds the job in the completed job queue."""
        if self.skip:
            return

        json_data = self.download_queue(current_page=_current_page)
        if not json_data:
            return

        jobs = json_data['jobs']
        first_id = jobs[0]['id']
        if _current_page == 1:
            self.last_id = first_id
        for job in jobs:
            cur_id = job.get('id')
            if cur_id == job_id:
                return job
            elif cur_id == last_id:
                return
        if _current_page >= max_depth or _current_page >= json_data.get('maxPages', 0):
            return

        return self.find_job(job_id, last_id, _current_page=_current_page + 1)

    def wait_for_job(self, job_id, timeout=_DEFAULT_TIMEOUT, delay=_DEFAULT_DELAY):
        """Waits until the job appears in the completed job queue."""
        if self.skip:
            return

        logger.debug('Waiting up to {} sec for completion of the job ID {}'.format(timeout, job_id))

        countdown = timeout
        while countdown > 0:
            job = self.find_job(job_id, self.last_id)
            if job:
                return job
            time.sleep(delay)
            countdown -= delay

        logger.error(
            'Timed out while waiting for completion of the job ID {}. '
            'Results not updated.'.format(job_id))

    # pylint: disable=no-self-use
    def _check_outcome(self, job):
        """Parses returned message and checks submit outcome."""
        status = job.get('status') if job else None
        if not status:
            return False

        if status.lower() == 'success':
            logger.info('Results successfully updated!')
            return True
        logger.error('Status = {}, results not updated'.format(status))
        return False

    # pylint: disable=no-self-use
    def _download_log(self, url, output_file):
        """Saves log returned by the message bus."""
        logger.info("Saving log {} to {}".format(url, output_file))

        def _do_log_download():
            try:
                return requests.get(url)
            # pylint: disable=broad-except
            except Exception as err:
                logger.error(err)

        # log file may not be ready yet, wait a bit
        for __ in range(5):
            log_data = _do_log_download()
            if log_data or log_data is None:
                break
            time.sleep(2)

        if not log_data:
            logger.error("Failed to download log file '{}'.".format(url))
            return
        with open(os.path.expanduser(output_file), 'wb') as out:
            out.write(log_data.content)

    def get_log(self, job, log_file=None):
        """Get log or log url of the job."""
        if not job:
            return

        url = job.get('logstashURL')
        if url:
            if log_file:
                self._download_log(url, log_file)
            else:
                logger.info('Submit log: {}'.format(url))

    def queue_init(self):
        """Initializes the instance with the last job in the completed queue."""
        if self.skip:
            return

        json_data = self.download_queue(jobs_per_page=1)
        if json_data:
            self.last_id = json_data['jobs'][0]['id']
            return True

        logger.error('Failed to initialize.')
        self.skip = True
        return False

    def verify_submit(self, job_id, timeout=_DEFAULT_TIMEOUT, delay=_DEFAULT_DELAY, **kwargs):
        """Verifies that the results were successfully submitted."""
        job = self.wait_for_job(job_id, timeout, delay)
        self.get_log(job, log_file=kwargs.get('log_file'))

        return self._check_outcome(job)
