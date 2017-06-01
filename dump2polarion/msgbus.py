# -*- coding: utf-8 -*-
# pylint: disable=logging-format-interpolation
"""
Connects to the Polarion® XUnit Importer message bus and verifies that results were submitted.
"""

from __future__ import unicode_literals, absolute_import

import os
import logging
import threading
import json
import pprint

from xml.etree import ElementTree

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

    def wait_for_message(self, timeout=300):
        """Waits for message on xunit importer message bus."""
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
        root = ElementTree.fromstring(xunit)
    except ElementTree.ParseError as err:
        logger.error(err)
        return
    properties = root.find('properties')
    for prop in properties:
        if prop.attrib.get('name') and 'polarion-response-' in prop.attrib['name']:
            return (prop.attrib['name'][len('polarion-response-'):], str(prop.attrib['value']))


def log_received_data(headers, message):
    """Logs received message and headers."""
    if not logger.isEnabledFor(logging.DEBUG) or headers is None or message is None:
        return
    pp = pprint.PrettyPrinter(indent=4)
    logging.debug("Message headers: \n{}".format(pp.pformat(headers)))
    logging.debug("Message body: \n{}".format(message))


def check_outcome(message, is_error):
    """Parses returned message and checks submit outcome."""
    if is_error is None:
        logger.error("Submit verification timed out, results probably not updated")
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
        logger.info("Submit log: {}".format(url))

    if data.get('status') == 'passed':
        logger.info("Results successfully submitted!")
        return True

    logger.error("Status = {}, results not updated".format(data.get('status')))
    return False


def get_verification_func(config, xunit, **kwargs):
    """Subscribes to the message bus and returns verification function."""
    bus_url = config.get('message_bus')
    if not bus_url:
        logger.error(
            "Message bus url ('message_bus') not configured, skipping submit verification")
        return

    selector = get_response_property(xunit)
    if not selector:
        logger.error(
            "The 'polarion-response-*' property not set, skipping submit verification")
        return

    login = kwargs.get('user') or config.get('username') or os.environ.get("POLARION_USERNAME")
    pwd = kwargs.get('password') or config.get('password') or os.environ.get("POLARION_PASSWORD")
    if not all([login, pwd]):
        logger.error("Missing credentials, skipping submit verification")
        return

    host, port = bus_url.split(':')
    conn = stomp.Connection([(host.encode('ascii', 'ignore'), int(port))])
    listener = XunitListener()
    conn.set_listener('XUnit Listener', listener)
    logger.debug('Subscribing to the XUnit Importer message bus')
    conn.start()
    conn.connect(login=login, passcode=pwd)

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

    def verify_submit(skip=False, timeout=300):
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

        return check_outcome(message, is_error)

    return verify_submit
