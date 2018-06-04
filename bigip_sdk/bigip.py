########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Standard Imports
import logging
import os
import time

# Third Party Imports
import requests

# Local Imports
from . import LOGGER_NAME
from .exceptions import BigipSyncException, BigipRestError, BigipAuthError

AUTH_ENDPOINT = "/mgmt/shared/authn/login"
SAVE_ENDPOINT = "/mgmt/tm/sys/config"
SYNC_ENDPOINT = "/mgmt/tm/cm/config-sync"
DEVICE_ENDPOINT = "/mgmt/tm/cm/device"
STATUS_ENDPOINT = "/mgmt/tm/cm/sync-status"
CERT_ENDPOINT = "/mgmt/tm/sys/crypto/cert"
KEY_ENDPOINT = "/mgmt/tm/sys/crypto/key"
FAILOVER_STATE = "failoverState"
STANDBY_STATE = "standby"
MGMT_IP = "managementIp"
ACTIVE_STATE = "active"
SELF_DEVICE = "selfDevice"
ITEMS = "items"
CMD = "command"
CMD_SAVE = "save"
CMD_RUN = "run"
CMD_UTIL_ARGS = "utilCmdArgs"
CMD_INSTALL = "install"
CMD_NAME = "name"
CMD_FROM_URL = "from-url"
SYNC_TO_GROUP = "to-group {0}"
ENTRIES = "entries"
NESTED_STATS = "nestedStats"
STATUS = "status"
SUMMARY = "summary"
DESCRIPTION = "description"
IN_SYNC = "In Sync"

log = logging.getLogger(LOGGER_NAME)


def install_cert(ip,
                 username,
                 passwd,
                 name,
                 key_url,
                 cert_url):
    key_name = "{0}.key".format(name)
    cert_name = "{0}.crt".format(name)

    session, ip = _get_ip_and_session(ip, username, passwd)

    key_payload = {}
    key_payload[CMD] = CMD_INSTALL
    key_payload[CMD_NAME] = key_name
    key_payload[CMD_FROM_URL] = key_url

    _make_rest_call(ip, KEY_ENDPOINT, session, 'POST', key_payload)

    cert_payload = {}
    cert_payload[CMD] = CMD_INSTALL
    cert_payload[CMD_NAME] = cert_name
    cert_payload[CMD_FROM_URL] = cert_url

    _make_rest_call(ip, CERT_ENDPOINT, session, 'POST', cert_payload)

    # Generate required data for interacting with certs later via this plugin
    # and iWorkflow plugin.
    # We don't currently retrieve the partition as only /Common/ is used. This
    # will need to be changed if other partitions are used.
    partition = '/Common'
    key_path = os.path.join(partition, key_name)
    cert_path = os.path.join(partition, cert_name)

    return {
        'partition': partition,
        'key_path': key_path,
        'cert_path': cert_path,
        'key_name': key_name,
        'cert_name': cert_name,
    }


def delete_cert(ip,
                username,
                passwd,
                key_name,
                cert_name):
    key_location = KEY_ENDPOINT + "/" + key_name
    cert_location = CERT_ENDPOINT + "/" + cert_name

    session, ip = _get_ip_and_session(ip, username, passwd)

    _make_rest_call(ip, cert_location, session, 'DELETE')
    _make_rest_call(ip, key_location, session, 'DELETE')


def do_sync(ip, sync_group, user, password, retry_timer):
    session, ip = _get_ip_and_session(ip, user, password)

    _request_save(ip, session)
    _request_sync(ip, sync_group, session)

    _await_status(ip, retry_timer, session)


def _get_ip_and_session(ip, user, password):
    session = setup_session(user, password, ip)
    active_ip = _get_device(ip, session)

    # log back in using Active device
    session = setup_session(user, password, active_ip)

    return session, active_ip


def _get_device(ip, session):
    resp = _make_rest_call(ip, DEVICE_ENDPOINT, session, 'GET')

    return _determine_active_device(ip, resp)


def _determine_active_device(current_ip, resp_devices):
    try:
        resp = resp_devices.json()
        self_device = _get_self_device(resp)
        self_device.get(MGMT_IP)
        if self_device.get(FAILOVER_STATE) == STANDBY_STATE:
            log.warn("Device is standby unit")
            return next(
                dev.get(MGMT_IP)
                for dev in resp.get(ITEMS)
                if dev.get(FAILOVER_STATE) == ACTIVE_STATE
            )
        else:
            return current_ip
    except Exception:
        raise BigipSyncException("Cannot find an active device")


def _get_self_device(devices):
    self_device_idx = 0

    while True:
        try:
            if devices.get(ITEMS)[self_device_idx].get(SELF_DEVICE) \
                    == "true":
                return devices.get(ITEMS)[self_device_idx]
            else:
                self_device_idx = self_device_idx + 1
        except Exception:
            raise BigipSyncException("Cannot find an active device")


def _request_save(ip, session):
    payload = dict()
    payload[CMD] = CMD_SAVE

    _make_rest_call(ip, SAVE_ENDPOINT, session, 'POST', payload)


def _request_sync(ip, sync_group, session):
    payload = dict()
    payload[CMD] = CMD_RUN
    payload[CMD_UTIL_ARGS] = \
        SYNC_TO_GROUP.format(sync_group)

    _make_rest_call(ip, SYNC_ENDPOINT, session, 'POST', payload)


def _make_url(ip, endpoint):
    return "https://{0}{1}".format(ip, endpoint)


def _raise_error_on_bad_response(call_type, response, ip, endpoint,
                                 payload=None, exception=BigipRestError):
    error_message = 'Error in {call_type} call to {url}'
    if payload:
        error_message += ' with payload {payload}.'
    else:
        error_message += '.'
    error_message += ' Response was {status}: {reason}.'

    if response.status_code != requests.codes.OK:
        raise exception(
            error_message.format(
                url=_make_url(ip, endpoint),
                payload=payload,
                status=response.status_code,
                reason=response.text,
                call_type=call_type
            )
        )


def _make_rest_call(ip, endpoint, session, method, payload=None):
    session_method = {
        'GET': session.get,
        'POST': session.post,
        'DELETE': session.delete,
    }[method]

    url = _make_url(ip, endpoint)

    resp = session_method(url, json=payload)
    _raise_error_on_bad_response(method, resp, ip, endpoint, payload)

    return resp


def _await_status(ip, retry_timer, session):
    while True:
        status_json = _make_rest_call(ip, STATUS_ENDPOINT,
                                      session, 'GET').json()
        entries = status_json \
            .get(ENTRIES) \
            .get(('https://{0}{1}/0'.format("localhost", STATUS_ENDPOINT))) \
            .get(NESTED_STATS) \
            .get(ENTRIES)

        status = entries.get(STATUS) \
            .get(DESCRIPTION)
        summary = entries.get(SUMMARY) \
            .get(DESCRIPTION)
        log.info("Status: {0}: {1}".format(status, summary))
        if status == IN_SYNC:
            break
        else:
            log.info("Retry in {0}s".format(retry_timer))
            time.sleep(retry_timer)


def setup_session(user, password, ip):
    session = requests.session()
    session.auth = (user, password)
    session.verify = False
    session.headers.update({'Content-Type': 'application/json'})

    # Get auth token
    auth_token = _get_auth_token(ip, user, password, session)
    session.headers.update({'X-F5-Auth-Token': auth_token})
    session.auth = None

    return session


def _get_auth_token(ip, user, password, session):
    auth_payload = {
        "username": user,
        "password": password,
        "loginProviderName": "tmos",
    }

    url = _make_url(ip, AUTH_ENDPOINT)

    resp = session.post(url, json=auth_payload)

    # Hide password in case we need an error response
    auth_payload['password'] = '********'
    _raise_error_on_bad_response(
        call_type='POST',
        response=resp,
        ip=ip,
        endpoint=AUTH_ENDPOINT,
        payload=auth_payload,
        exception=BigipAuthError,
    )

    token = resp.json()['token']['token']

    return token
