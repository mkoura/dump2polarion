# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Connects to the Polarion XUnit Importer message bus and verifies that results were submitted.
"""

from __future__ import unicode_literals, absolute_import

import os
import logging
import threading
import time
import json
import pprint

from xml.etree import ElementTree

import requests
import stomp


# pylint: disable=invalid-name
logger = logging.getLogger(__name__)
logging.getLogger('stomp.py').setLevel(logging.WARNING)


class XunitListener(object):
    """Listener for xunit importer message bus."""
    def __init__(self):
        self.message_list = []
        self.message_condition = threading.Condition()
        self.message_received = False

    def on_message(self, headers, message, is_error=False):
        """Actions when message is received."""
        self.message_list.append((headers, message, is_error))
        with self.message_condition:
            self.message_received = True
            self.message_condition.notify()

    def on_error(self, headers, message):
        """Actions when error is received."""
        return self.on_message(headers, message, True)

    def wait_for_message(self, timeout=None):
        """Waits for message on xunit importer message bus."""
        timeout = timeout or 300
        with self.message_condition:
            if not self.message_received:
                self.message_condition.wait(timeout=timeout)
        retval = self.message_received
        self.message_received = False
        return retval

    def get_latest_message(self):
        """Returns last received message."""
        return self.message_list[-1]


def get_response_property(xunit):
    """Parse xunit xml and finds the "polarion-response-" name and value."""
    try:
        root = ElementTree.fromstring(xunit.encode('utf-8'))
    except ElementTree.ParseError as err:
        logger.error(err)
        return

    if root.tag == 'testsuites':
        properties = root.find('properties')
        for prop in properties:
            prop_name = prop.get('name', '')
            if 'polarion-response-' in prop_name:
                return (prop_name[len('polarion-response-'):], str(prop.get('value')))
    elif root.tag == 'testcases':
        properties = root.find('response-properties')
        for prop in properties:
            if prop.tag != 'response-property':
                continue
            prop_name = prop.get('name')
            prop_value = prop.get('value')
            if prop_name and prop_value:
                return (prop_name, str(prop_value))


def log_received_data(headers, message):
    """Logs received message and headers."""
    if not logger.isEnabledFor(logging.DEBUG) or headers is None or message is None:
        return
    pp = pprint.PrettyPrinter(indent=4)
    logging.debug("Message headers: \n{}".format(pp.pformat(headers)))
    logging.debug("Message body: \n{}".format(message))


def download_log(url, output_file):
    """Saves log returned by the message bus."""
    logger.info("Saving log {} to {}".format(url, output_file))

    def _do_log_download():
        try:
            return requests.get(url)
        # pylint: disable=broad-except
        except Exception as err:
            logger.error(err)

    # log file may not be ready yet, wait a bit
    for _ in range(5):
        log_data = _do_log_download()
        if log_data or log_data is None:
            break
        time.sleep(1)

    if not log_data:
        logger.error("Failed to download log file '{}'.".format(url))
    with open(os.path.expanduser(output_file), 'wb') as out:
        out.write(log_data.content)


def check_outcome(message, is_error, log_file=None):
    """Parses returned message and checks submit outcome."""
    if is_error is None:
        logger.error("Submit verification timed out, check in the web UI if results were updated "
                     "(might take a while, please don't resubmit)")
        return False
    elif is_error:
        logger.error("Received an error, results not updated")
        return False

    try:
        data = json.loads(message)
    # pylint: disable=broad-except
    except Exception:
        logger.error("Cannot parse message, results probably not updated")
        return False

    url = data.get('log-url')
    if url:
        if not log_file:
            logger.info("Submit log: {}".format(url))
        else:
            download_log(url, log_file)

    if data.get('status') == 'passed':
        logger.info("Results successfully submitted!")
        return True

    logger.error("Status = {}, results not updated".format(data.get('status')))
    return False


def get_verification_func(bus_url, xunit, user, password, **kwargs):
    """Subscribes to the message bus and returns verification function."""
    if not bus_url:
        logger.error(
            "Message bus url ('message_bus') not configured, skipping submit verification")
        return

    selector = get_response_property(xunit)
    if not selector:
        logger.error(
            "The 'polarion-response-*' property not set, skipping submit verification")
        return

    if not all([user, password]):
        logger.error("Missing credentials, skipping submit verification")
        return

    host, port = bus_url.split(':')
    conn = stomp.Connection([(host.encode('ascii', 'ignore'), int(port))])
    listener = XunitListener()
    conn.set_listener('XUnit Listener', listener)
    logger.debug('Subscribing to the XUnit Importer message bus')
    conn.start()
    conn.connect(login=user, passcode=password)

    try:
        conn.subscribe(
            destination='/topic/CI',
            id=1,
            ack='auto',
            headers={'selector': "{}='{}'".format(selector[0], selector[1])}
        )
    # pylint: disable=broad-except
    except Exception as err:
        logger.error("Skipping submit verification: {}".format(err))
        logger.debug('Terminating subscription')
        conn.disconnect()

    def verify_submit(skip=False, timeout=None):
        """Verifies that the results were successfully submitted."""
        headers = message = is_error = None
        try:
            if skip:
                # just do cleanup in finally
                return
            logger.info("Waiting for response on the XUnit Importer message bus...")
            if listener.wait_for_message(timeout=timeout):
                headers, message, is_error = listener.get_latest_message()
        # pylint: disable=broad-except
        except Exception as err:
            logger.error("Skipping submit verification: {}".format(err))
        finally:
            logger.debug('Terminating subscription')
            conn.disconnect()

        log_received_data(headers, message)

        return check_outcome(message, is_error, log_file=kwargs.get('log_file'))

    return verify_submit
