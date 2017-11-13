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

import requests
import time
import logging

from . import LOGGER_NAME

from .exceptions import BigipSyncException


SAVE_ENDPOINT = "/mgmt/tm/sys/config"
SYNC_ENDPOINT = "/mgmt/tm/cm/config-sync"
DEVICE_ENDPOINT = "/mgmt/tm/cm/device"
STATUS_ENDPOINT = "/mgmt/tm/cm/sync-status"
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
SYNC_TO_GROUP = "to-group {0}"
ENTRIES = "entries"
NESTED_STATS = "nestedStats"
STATUS = "status"
SUMMARY = "summary"
DESCRIPTION = "description"
IN_SYNC = "In Sync"


log = logging.getLogger(LOGGER_NAME)


def do_sync(ip, sync_group, user, password, retry_timer):
    session = setup_session(user, password)

    active_ip = _get_device(ip, session)

    _request_save(active_ip, session)
    _request_sync(active_ip, sync_group, session)

    _await_status(active_ip, retry_timer, session)


def _get_device(ip, session):
    resp = _do_get(ip, DEVICE_ENDPOINT, session)

    return _determine_active_device(ip, resp)


def _determine_active_device(current_ip, resp_devices):
    try:
        resp = resp_devices.json()
        self_device = _get_self_device(resp)
        self_ip = self_device.get(MGMT_IP)
        if self_device.get(FAILOVER_STATE) == STANDBY_STATE:
            log.warn("Device is standby unit")
            return next(
                dev.get(MGMT_IP)
                for dev in resp.get(ITEMS)
                if dev.get(FAILOVER_STATE) == ACTIVE_STATE
            )
        else:
            return self_ip
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

    _do_post(ip, SAVE_ENDPOINT, payload, session)


def _request_sync(ip, sync_group, session):
    payload = dict()
    payload[CMD] = CMD_RUN
    payload[CMD_UTIL_ARGS] = \
        SYNC_TO_GROUP.format(sync_group)

    _do_post(ip, SYNC_ENDPOINT, payload, session)


def _do_post(ip, endpoint, payload, session):
    resp = session.post(
        "https://{0}{1}".format(ip, endpoint),
        json=payload
    )

    if resp.status_code != requests.codes.OK:
        raise BigipSyncException("Received unsupported status code={}".format(
            resp.status_code
        ))

    return resp


def _do_get(ip, endpoint, session):
    resp = session.get("https://{0}{1}".format(ip, endpoint))

    if resp.status_code != requests.codes.OK:
        raise BigipSyncException("Received unsupported status code={}".format(
            resp.status_code
        ))

    return resp


def _await_status(ip, retry_timer, session):
    while True:
        status_json = _do_get(ip, STATUS_ENDPOINT, session).json()
        entries = status_json \
            .get(ENTRIES) \
            .get(
                ('https://{0}{1}/0'.format("localhost",
                                           STATUS_ENDPOINT))) \
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


def setup_session(user, password):
    session = requests.session()
    session.auth = (user, password)
    session.verify = False
    session.headers.update({'Content-Type': 'application/json'})
    return session
