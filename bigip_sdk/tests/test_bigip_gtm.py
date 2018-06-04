########
# Copyright (c) 2018 GigaSpaces Technologies Ltd. All rights reserved
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
import unittest

# Third Party Imports
import requests_mock

# Local Imports
from bigip_sdk import gtm
from bigip_sdk import exceptions

# GTM Connection Params
IP = 'localhost'
USER = 'user'
PASSWORD = 'test'


VS_SUCCESS_RESPONSE =\
    {
        "name": "/Common/vs3",
        "destination": "10.244.51.11:443",
        "fullPath": "/Common/vs3",
        "limitMaxConnections": 0,
        "translationAddress": "none",
    }

POOL_SUCCESS_RESPONSE = \
    {
      "loadBalancingMode": "round-robin",
      "fallbackMode": "return-to-dns",
      "fullPath": "/Common/pool-test",
      "name": "pool-test",
      "fallbackIp": "any",
      "qosPacketRate": 1,
      "partition": "Common",
    }

POOL_MEMBER_SUCCESS_RESPONSE = \
    {
      "name": "vs3",
      "partition": "Common",
      "subPath": "LAB-TEST:/Common",
      "fullPath": "/Common/LAB-TEST:/Common/vs3",
      "memberOrder": 0
    }

WIP_SUCCESS_RESPONSE = \
    {

      "name": "test-wip01.local",
      "partition": "Common",
      "pools": [
        {
          "partition": "Common",
          "ratio": 1,
          "order": 0,
          "name": "pool-test",
          "nameReference": {
            "link": "https://localhost/mgmt/tm/gtm/pool/a/"
                    "~Common~pool1-test?ver=12.1.2"
          }
        }
      ],
      "fullPath": "/Common/test-wip01.local",
    }


DELETE_ERROR_RESPONSE = \
    {
        'errorStack': [],
        'message': 'ERROR WHILE TRYING TO CREATE RESOURCE',
        'code': 400,
        'apiError': 3
    }

DELETE_ERROR_RESPONSE = \
    {
        'errorStack': [],
        'message': 'ERROR WHILE TRYING TO DELETE RESOURCE',
        'code': 404,
        'apiError': 3
    }


class GTMTestCase(unittest.TestCase):
    def setUp(self):
        self.gtm = gtm.GTM(ip=IP, user=USER, password=PASSWORD)
        self.partition = 'Common'
        self.record_type = 'A'
        self.gtm_server = 'LAB-TEST'

    def test_create_virtual_server_success(self):
        uri = "server/~{0}~{1}/virtual-servers".format(self.partition,
                                                       self.gtm_server)
        payload_request = \
            {
                'destination': '10.244.51.11:443',
                'name': 'vs3',
                'translationAddress': 'none',
            }
        full_url = gtm.BASE_URL.format(IP, uri)

        with requests_mock.mock() as m:
            m.post(full_url, status_code=200, json=VS_SUCCESS_RESPONSE)
            result = self.gtm.add_vs(self.partition,
                                     self.gtm_server,
                                     payload_request)

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], '/{0}/{1}'
                         .format(self.partition, payload_request['name']))

        self.assertEqual(result['destination'], payload_request['destination'])
        self.assertEqual(result['translationAddress'],
                         payload_request['translationAddress'])

    def test_create_virtual_server_failure(self):
        self.gtm_server = 'INVALID-LTM-SERVER'
        uri = "server/~{0}~{1}/virtual-servers".format(self.partition,
                                                       self.gtm_server)
        payload_request = \
            {
                'destination': '10.244.51.11:443',
                'name': 'vs3',
                'translationAddress': 'none',
            }
        full_url = gtm.BASE_URL.format(IP, uri)

        with requests_mock.mock() as m:
            m.post(full_url, status_code=400, json=DELETE_ERROR_RESPONSE)
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.add_vs(self.partition,
                                self.gtm_server,
                                payload_request)

    def test_delete_virtual_server_success(self):
        vs_name = 'vs3'
        uri = "server/~{0}~{1}/virtual-servers/~{0}~{2}".format(
            self.partition, self.gtm_server, vs_name)

        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.delete(full_url, status_code=200, json={})
            result = self.gtm.delete_vs(self.partition,
                                        self.gtm_server,
                                        vs_name)
        self.assertEqual(result, {})

    def test_delete_virtual_server_failure(self):
        vs_name = 'NOT-FOUND-SERVER'
        uri = "server/~{0}~{1}/virtual-servers/~{0}~{2}".format(
            self.partition, self.gtm_server, vs_name)

        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.delete(full_url, status_code=404, json={})
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.delete_vs(self.partition,
                                   self.gtm_server,
                                   vs_name)

    def test_create_pool_success(self):
        uri = "pool/{0}".format(self.record_type)
        payload_request = \
            {
                'alternateMode': 'round-robin',
                'fallbackIp': 'any',
                'fallbackMode': 'return-to-dns',
                'loadBalancingMode': 'round-robin',
                'manualResume': 'disabled',
                'name': 'pool-test',
                'ttl': 0,
                'partition': 'Common',
            }
        full_url = gtm.BASE_URL.format(IP, uri)

        with requests_mock.mock() as m:
            m.post(full_url, status_code=200, json=POOL_SUCCESS_RESPONSE)
            result = self.gtm.create_pool(self.record_type, payload_request)

        self.assertIsNotNone(result)

        self.assertEqual(result['fullPath'], '/{0}/{1}'
                         .format(self.partition, payload_request['name']))

        self.assertEqual(result['name'], payload_request['name'])

        self.assertEqual(result['loadBalancingMode'],
                         payload_request['loadBalancingMode'])

        self.assertEqual(result['fallbackIp'],
                         payload_request['fallbackIp'])

        self.assertEqual(result['fallbackMode'],
                         payload_request['fallbackMode'])

    def test_create_pool_failure(self):
        uri = "pool/{0}".format(self.record_type)
        payload_request = {}
        full_url = gtm.BASE_URL.format(IP, uri)

        with requests_mock.mock() as m:
            m.post(full_url, status_code=400, json=DELETE_ERROR_RESPONSE)
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.create_pool(self.record_type, payload_request)

    def test_delete_pool_success(self):
        pool_name = 'pool-test'
        uri = "pool/{1}/~{0}~{2}".format(self.partition,
                                         self.record_type,
                                         pool_name)

        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.delete(full_url, status_code=200, json={})
            result = self.gtm.delete_pool(self.partition,
                                          self.record_type,
                                          pool_name)

        self.assertEqual(result, {})

    def test_delete_pool_failure(self):
        pool_name = 'INVALID-POOL-NAME'
        uri = "pool/{1}/~{0}~{2}".format(self.partition,
                                         self.record_type,
                                         pool_name)

        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.delete(full_url, status_code=404, json={})
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.delete_pool(self.partition,
                                     self.record_type,
                                     pool_name)

    def test_add_pool_members_success(self):
        pool_name = 'pool-test'
        uri = "pool/{1}/~{0}~{2}/members"\
            .format(self.partition, self.record_type, pool_name)

        payload_request = \
            {
                'memberOrder': 0,
                'name': 'vs3',
                'partition': 'Common'
            }
        full_url = gtm.BASE_URL.format(IP, uri)

        with requests_mock.mock() as m:
            m.post(full_url, status_code=200,
                   json=POOL_MEMBER_SUCCESS_RESPONSE)

            result = self.gtm.add_pool_members(self.partition,
                                               self.record_type,
                                               pool_name,
                                               payload_request)

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], payload_request['name'])
        self.assertEqual(result['partition'], payload_request['partition'])
        self.assertEqual(result['memberOrder'], payload_request['memberOrder'])
        self.assertEqual(result['subPath'],
                         '{0}:/{1}'.format(self.gtm_server, self.partition))
        self.assertEqual(
            result['fullPath'], '/{0}/{1}:/{2}/vs3'.format(
                self.partition, self.gtm_server, self.partition,))

    def test_add_pool_members_failure(self):
        pool_name = 'INVALID-POOL'
        uri = "pool/{1}/~{0}~{2}/members"\
            .format(self.partition, self.record_type, pool_name)

        payload_request = \
            {
                'memberOrder': 0,
                'name': 'vs3',
                'partition': 'Common'
            }
        full_url = gtm.BASE_URL.format(IP, uri)

        with requests_mock.mock() as m:
            m.post(full_url, status_code=400, json=DELETE_ERROR_RESPONSE)
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.add_pool_members(self.partition,
                                          self.record_type,
                                          pool_name,
                                          payload_request)

        payload_request = {}
        with requests_mock.mock() as m:
            m.post(full_url, status_code=400, json=DELETE_ERROR_RESPONSE)
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.add_pool_members(self.partition,
                                          self.record_type,
                                          pool_name,
                                          payload_request)

    def test_create_wip_success(self):
        pool_name = 'pool-test'
        uri = "wideip/{0}".format(self.record_type)

        payload_request = \
            {
                'name': 'test-wip01.local',
                'persistence': 'enabled',
                'ttlPersistence': '3600',
                'pools':
                    [
                        {
                            'name': 'pool-test',
                            'partition': 'Common',
                        }
                    ]

            }
        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.post(full_url, status_code=200, json=WIP_SUCCESS_RESPONSE)
            result = self.gtm.create_wip(self.record_type, payload_request)

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], payload_request['name'])
        self.assertEqual(result['pools'][0]['name'], pool_name)
        self.assertEqual(result['pools'][0]['partition'], self.partition)

        self.assertEqual(result['fullPath'],
                         '/{0}/{1}'.format(self.partition,
                                           payload_request['name'],))

    def test_create_wip_failure(self):
        uri = "wideip/{0}".format(self.record_type)

        payload_request = \
            {
                'name': 'test-wip01.local',
                'persistence': 'enabled',
                'ttlPersistence': '3600',
                'pools':
                    [
                        {
                            'name': 'INVALID-POOL',
                            'partition': 'Common',
                        }
                    ]

            }
        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.post(full_url, status_code=400, json=DELETE_ERROR_RESPONSE)
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.create_wip(self.record_type, payload_request)

        payload_request = {}
        with requests_mock.mock() as m:
            m.post(full_url, status_code=400, json=DELETE_ERROR_RESPONSE)
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.create_wip(self.record_type, payload_request)

    def test_delete_wip_success(self):
        wip_name = 'test-wip01.local'
        uri = "wideip/{1}/~{0}~{2}".format(self.partition,
                                           self.record_type, wip_name)

        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.delete(full_url, status_code=200, json={})
            result = self.gtm.delete_wip(self.partition,
                                         self.record_type,
                                         wip_name)

        self.assertEqual(result, {})

    def test_delete_wip_failure(self):
        wip_name = 'INVALID-wip-NAME'
        uri = "wideip/{1}/~{0}~{2}".format(self.partition,
                                           self.record_type, wip_name)

        full_url = gtm.BASE_URL.format(IP, uri)
        with requests_mock.mock() as m:
            m.delete(full_url, status_code=404, json={})
            with self.assertRaises(exceptions.GTMAPIException):
                self.gtm.delete_wip(self.partition,
                                    self.record_type,
                                    wip_name)
