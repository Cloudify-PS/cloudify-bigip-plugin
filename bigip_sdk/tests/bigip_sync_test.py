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


import unittest
import requests_mock

from bigip_sdk import bigip
from bigip_sdk.exceptions import BigipSyncException

base_ip = '1.2.3.4'
sync_group = 'group1'
user = 'user1'
password = 'password1'


def url_get_device(ip=base_ip):
    return 'https://{}{}'.format(ip, bigip.DEVICE_ENDPOINT)


def url_save_device(ip=base_ip):
    return 'https://{}{}'.format(ip, bigip.SAVE_ENDPOINT)


def url_sync_device(ip=base_ip):
    return 'https://{}{}'.format(ip, bigip.SYNC_ENDPOINT)


def url_status(ip=base_ip):
    return 'https://{}{}'.format(ip, bigip.STATUS_ENDPOINT)


def device_response(self_device="true",
                    failover_state="active",
                    second_self_device="true",
                    second_failover_state="active",
                    mgmt_ip=base_ip):
    return {
        'items': [
            {
                'selfDevice': self_device,
                'failoverState': failover_state,
                'managementIp': mgmt_ip
            },
            {
                'selfDevice': second_self_device,
                'failoverState': second_failover_state,
                'managementIp': mgmt_ip
            },
        ]
    }


def status_response(sync_status=bigip.IN_SYNC):
    return {
        'entries': {
            'https://localhost{}/0'.format(bigip.STATUS_ENDPOINT): {
                'nestedStats': {
                    'entries': {
                        'status': {
                            'description': sync_status
                        },
                        'summary': {
                            'description': 'summary1'
                        }
                    }
                }
            }
        }
    }


class BigipSyncTest(unittest.TestCase):

    def test_sync_success(self):
        # given
        resp_get_device = device_response()
        resp_get_status = status_response()

        with requests_mock.mock() as m:
            m.get(url_get_device(), json=resp_get_device, status_code=200)
            m.post(url_save_device(), status_code=200)
            m.post(url_sync_device(), status_code=200)
            m.get(url_status(), json=resp_get_status, status_code=200)

            # when
            result = bigip.do_sync(base_ip, sync_group, user, password, 10)

        # then
        self.assertIsNone(result)

    def test_sync_success_standby(self):
        # given
        mgmt_ip = '1.2.3.5'
        resp_get_device = device_response(failover_state="standby",
                                          mgmt_ip=mgmt_ip)
        resp_get_status = status_response()

        with requests_mock.mock() as m:
            m.get(url_get_device(base_ip),
                  json=resp_get_device,
                  status_code=200)
            m.get(url_get_device(mgmt_ip),
                  json=resp_get_device,
                  status_code=200)
            m.post(url_save_device(mgmt_ip), status_code=200)
            m.post(url_sync_device(mgmt_ip), status_code=200)
            m.get(url_status(mgmt_ip), json=resp_get_status, status_code=200)

            # when
            result = bigip.do_sync(base_ip, sync_group, user, password, 10)

        self.assertIsNone(result)

    def test_sync_success_no_self_device(self):
        # given
        mgmt_ip = '1.2.3.5'
        resp_get_device = device_response(self_device="false",
                                          failover_state="standby",
                                          mgmt_ip=mgmt_ip)
        resp_get_status = status_response()

        with requests_mock.mock() as m:
            m.get(url_get_device(base_ip),
                  json=resp_get_device,
                  status_code=200)
            m.get(url_get_device(mgmt_ip),
                  json=resp_get_device,
                  status_code=200)
            m.post(url_save_device(mgmt_ip), status_code=200)
            m.post(url_sync_device(mgmt_ip), status_code=200)
            m.get(url_status(mgmt_ip), json=resp_get_status, status_code=200)

            # when
            result = bigip.do_sync(base_ip, sync_group, user, password, 10)

        self.assertIsNone(result)

    def test_sync_failure_get_400(self):
        # given
        resp_get_device = device_response()
        error_code = 400
        expected_error = 'Received unsupported status code={}'.format(
            error_code
        )

        with requests_mock.mock() as m:
            # then
            with self.assertRaisesRegexp(BigipSyncException,
                                         expected_error):
                m.get(url_get_device(base_ip),
                      json=resp_get_device,
                      status_code=400)

                # when
                bigip.do_sync(base_ip, sync_group, user, password, 10)

    def test_sync_failure_post_400(self):
        # given
        resp_get_device = device_response()
        error_code = 400
        expected_error = 'Received unsupported status code={}'.format(
            error_code
        )

        with requests_mock.mock() as m:
            # then
            with self.assertRaisesRegexp(BigipSyncException,
                                         expected_error):
                m.get(url_get_device(base_ip),
                      json=resp_get_device,
                      status_code=200)
                m.post(url_save_device(base_ip), status_code=400)

                # when
                bigip.do_sync(base_ip, sync_group, user, password, 10)

    def test_sync_no_self_device(self):
        # given
        resp_get_device = device_response(self_device="false",
                                          second_self_device="false")
        expected_error = 'Cannot find an active device'

        with requests_mock.mock() as m:
            # then
            with self.assertRaisesRegexp(BigipSyncException,
                                         expected_error):
                m.get(url_get_device(base_ip),
                      json=resp_get_device,
                      status_code=200)

                # when
                bigip.do_sync(base_ip, sync_group, user, password, 10)

    def test_sync_no_active_device(self):
        # given
        resp_get_device = device_response(failover_state="standby",
                                          second_failover_state="standby")
        expected_error = 'Cannot find an active device'

        with requests_mock.mock() as m:
            # then
            with self.assertRaisesRegexp(BigipSyncException,
                                         expected_error):
                m.get(url_get_device(base_ip),
                      json=resp_get_device,
                      status_code=200)

                # when
                bigip.do_sync(base_ip, sync_group, user, password, 10)
