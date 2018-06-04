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
from cloudify.mocks import MockCloudifyContext
from cloudify.state import current_ctx
from mock import MagicMock, patch


# Local Imports
from bigip_plugin import bigip_gtm


VS_SUCCESS_RESPONSE =\
    {
        "name": "/TEST-PARTITION/TEST-VIRTUAL-SERVER",
        "destination": "LOCALHOST",
        "fullPath": "/TEST-PARTITION/TEST-VIRTUAL-SERVER",
        "limitMaxConnections": 0,
        "translationAddress": "none",
    }

POOL_SUCCESS_RESPONSE = \
    {
      "loadBalancingMode": "TEST-LOADBALANCING-MODE",
      "fallbackMode": "TEST-FALLBACK-MODE",
      "fullPath": "/TEST-PARTITION/TEST-POOL",
      "name": "TEST-POOL-NAME",
      "fallbackIp": "TEST-FALLBACK-IP",
      "qosPacketRate": 1,
      "partition": "TEST-PARTITION",
    }

POOL_MEMBER_SUCCESS_RESPONSE = \
    {
      "name": "vs3",
      "partition": "TEST-PARTITION",
      "subPath": "LAB-TEST:/TEST-PARTITION",
      "fullPath": "/TEST-PARTITION/LAB-TEST:/TEST-PARTITION/TEST-VIRTUAL"
                  "-SERVER",
      "memberOrder": 0
    }

WIP_SUCCESS_RESPONSE = \
    {

      "name": "TEST-WIP1.LOCAL",
      "partition": "TEST-PARTITION",
      "pools": [
        {
          "partition": "TEST-PARTITION",
          "ratio": 1,
          "order": 0,
          "name": "TEST-POOL-NAME",
          "nameReference": {
            "link": "https://localhost/mgmt/tm/gtm/pool/a/"
                    "~TEST-PARTITION~TEST-POOL-NAME?ver=12.1.2"
          }
        }
      ],
      "fullPath": "/TEST-PARTITION/TEST-WIP1.LOCAL",
    }


class GTMTestCase(unittest.TestCase):
    def setUp(self):
        self.gtm_server = 'TEST-SERVER'
        self.partition = 'TEST-PARTITION'
        self.record_type = 'TEST-RECORD-TYPE'

        self.virtual_server_config =\
            [
                {
                    'destination': 'TEST-LOCAL-DEST',
                    'name': 'TEST-VIRTUAL-SERVER-1',
                    'translationAddress': 'none',
                },
            ]

        self.pool_config = {
            'alternateMode': 'TEST-ALTERNATE-MODE',
            'fallbackIp': 'TEST-FALLBACK-IP',
            'fallbackMode': 'TEST-FALLBACK-MODE',
            'loadBalancingMode': 'TEST-LOADBALANCING-MODE',
            'manualResume': 'TEST-MANUAL-RESUME',
            'name': 'TEST-POOL-NAME',
            'ttl': 0,
            'partition': 'TEST-PARTITION',
        }

        self.pool_member_config = \
            [
                {
                    'memberOrder': 0,
                    'name': 'TEST-VIRTUAL-SERVER-1',
                    'partition': 'TEST-PARTITION'
                },
            ]

        self.wip_config = {
            'name': 'TEST-WIP1.LOCAL',
            'persistence': 'TEST-PERSISTENCE',
            'ttlPersistence': '3600',
            'pools':
                [
                    {
                        'name': 'TEST-POOL-NAME',
                        'partition': 'TEST-PARTITION',
                    }
                ]
        }

        self.igtm_client = MagicMock()
        super(GTMTestCase, self).setUp()

    def tearDown(self):
        current_ctx.clear()

    def _prepare_loadbalancer_node(self):
        properties = {
            'ip': 'localhost',
            'user': 'test',
            'password': 'test',
            'partition': 'TEST-PARTITION',
            'record_type': 'TEST-RECORD-TYPE',
            'gtm_server': 'TEST-SERVER',
            'virtual_server_config': self.virtual_server_config,
            'pool_config': self.pool_config,
            'pool_member_config': self.pool_member_config,
            'wip_config': self.wip_config
        }

        _ctx = MockCloudifyContext(
            node_id="gtm_loadbalancer_id",
            node_name="gtm_loadbalancer_name",
            deployment_id="gtm_loadbalancer_name",
            properties=properties,
            runtime_properties={},
            relationships=[],
            operation={'retry_number': 0}
        )
        _ctx._node.type = 'cloudify.nodes.bigip.gtm.DNSLoadBalancer'

        current_ctx.set(_ctx)
        return _ctx

    def test_create_virtual_server(self):
        _ctx = self._prepare_loadbalancer_node()
        self.igtm_client.add_vs = MagicMock(return_value=VS_SUCCESS_RESPONSE)
        resource_config =\
            {
               'kwargs': self.virtual_server_config
            }
        bigip_gtm._manage_multiple_virtual_servers(_ctx,
                                                   self.igtm_client,
                                                   self.partition,
                                                   self.gtm_server,
                                                   resource_config)

        response = _ctx.instance.runtime_properties.get('virtual_servers')
        gtm_server = _ctx.instance.runtime_properties.get('gtm_server')
        partition = _ctx.instance.runtime_properties.get('partition')

        self.assertEqual(response[0], VS_SUCCESS_RESPONSE)
        self.assertEqual(gtm_server, self.gtm_server)
        self.assertEqual(partition, self.partition)
        self.assertEqual(response[0]['name'], VS_SUCCESS_RESPONSE['name'])

    def test_delete_virtual_server(self):
        self.igtm_client.delete_vs = MagicMock(return_value={})

        _ctx = self._prepare_loadbalancer_node()

        _ctx.instance.runtime_properties['virtual_servers']\
            = [VS_SUCCESS_RESPONSE]
        _ctx.instance.runtime_properties['partition'] = self.partition
        _ctx.instance.runtime_properties['gtm_server'] = self.gtm_server

        bigip_gtm._delete_virtual_servers(_ctx, self.igtm_client, )
        self.assertTrue(self.igtm_client.delete_vs.assert_called)
        self.assertTrue('virtual_servers'
                        not in _ctx.instance.runtime_properties)
        self.assertTrue('partition' not in _ctx.instance.runtime_properties)
        self.assertTrue('gtm_server' not in _ctx.instance.runtime_properties)

    def test_create_server_pool(self):
        _ctx = self._prepare_loadbalancer_node()
        self.igtm_client.create_pool = MagicMock(
            return_value=POOL_SUCCESS_RESPONSE)

        resource_config =\
            {
               'kwargs': self.pool_config
            }
        bigip_gtm._create_server_pool(_ctx,
                                      self.igtm_client,
                                      self.record_type,
                                      resource_config)

        response = _ctx.instance.runtime_properties.get('pool')
        pool_name = _ctx.instance.runtime_properties.get('pool_name')
        record_type = _ctx.instance.runtime_properties.get('record_type')

        self.assertEqual(response, POOL_SUCCESS_RESPONSE)
        self.assertEqual(pool_name, self.pool_config['name'])
        self.assertEqual(record_type, self.record_type)

    def test_delete_server_pool(self):
        pool_name = self.pool_config['name']
        self.igtm_client.delete_pool = MagicMock(return_value={})
        _ctx = self._prepare_loadbalancer_node()

        _ctx.instance.runtime_properties['pool'] = POOL_MEMBER_SUCCESS_RESPONSE
        _ctx.instance.runtime_properties['pool_members']\
            = POOL_MEMBER_SUCCESS_RESPONSE
        _ctx.instance.runtime_properties['partition'] = self.partition
        _ctx.instance.runtime_properties['pool_name'] = pool_name
        _ctx.instance.runtime_properties['record_type'] = self.record_type

        bigip_gtm._delete_server_pool(_ctx, self.igtm_client,)
        self.assertTrue(self.igtm_client.delete_pool.assert_called)
        self.assertTrue('pool' not in _ctx.instance.runtime_properties)
        self.assertTrue('pool_members' not in _ctx.instance.runtime_properties)
        self.assertTrue('pool_name' not in _ctx.instance.runtime_properties)
        self.assertTrue('record_type' not in _ctx.instance.runtime_properties)

    def test_add_pool_member(self):
        _ctx = self._prepare_loadbalancer_node()
        self.igtm_client.add_pool_members = MagicMock(
            return_value=POOL_MEMBER_SUCCESS_RESPONSE)

        resource_config =\
            {
               'kwargs': self.pool_member_config
            }

        virtual_servers = VS_SUCCESS_RESPONSE
        virtual_servers['IsAddedManually'] = True
        _ctx.instance.runtime_properties['virtual_servers'] = [virtual_servers]

        bigip_gtm._manage_pool_members(_ctx,
                                       self.igtm_client,
                                       self.record_type,
                                       self.gtm_server,
                                       resource_config)

        response = _ctx.instance.runtime_properties.get('pool_members')
        self.assertEqual(response[0], POOL_MEMBER_SUCCESS_RESPONSE)

    def test_create_wip(self):
        _ctx = self._prepare_loadbalancer_node()
        self.igtm_client.create_wip = MagicMock(
            return_value=WIP_SUCCESS_RESPONSE)

        resource_config =\
            {
               'kwargs': self.wip_config
            }

        bigip_gtm._create_wip(_ctx,
                              self.igtm_client,
                              self.record_type,
                              resource_config)

        response = _ctx.instance.runtime_properties.get('wip')
        wip_name = _ctx.instance.runtime_properties.get('wip_name')

        self.assertEqual(response, WIP_SUCCESS_RESPONSE)
        self.assertEqual(wip_name, self.wip_config['name'])

    def test_delete_wip(self):
        self.igtm_client.delete_wip = MagicMock(return_value={})
        wip_name = self.wip_config['name']
        _ctx = self._prepare_loadbalancer_node()
        _ctx.instance.runtime_properties['wip'] = WIP_SUCCESS_RESPONSE
        _ctx.instance.runtime_properties['partition'] = self.partition
        _ctx.instance.runtime_properties['wip_name'] = wip_name
        _ctx.instance.runtime_properties['record_type'] = self.record_type

        bigip_gtm._delete_wip(_ctx, self.igtm_client,)
        self.assertTrue(self.igtm_client.delete_wip.assert_called)
        self.assertTrue('wip' not in _ctx.instance.runtime_properties)
        self.assertTrue('wip_name' not in _ctx.instance.runtime_properties)

    @patch('bigip_plugin.bigip_gtm._create_wip')
    @patch('bigip_plugin.bigip_gtm._add_pool_member')
    @patch('bigip_plugin.bigip_gtm._create_server_pool')
    @patch('bigip_plugin.bigip_gtm._manage_multiple_virtual_servers')
    def test_create_dns_loadbalancer(self,
                                     vs_mock,
                                     pool_mock,
                                     pool_member_mock,
                                     wip_mock):

        _ctx = self._prepare_loadbalancer_node()

        virtual_servers = VS_SUCCESS_RESPONSE
        virtual_servers['IsAddedManually'] = True
        _ctx.instance.runtime_properties['virtual_servers'] = [virtual_servers]

        virtual_server_config = {'kwargs': self.virtual_server_config}
        pool_config = {'kwargs': self.pool_config}
        pool_member_config = {'kwargs': self.pool_member_config}
        wip_config = {'kwargs': self.wip_config}

        bigip_gtm.create_dns_loadbalancer(
            ctx=_ctx,
            igtm=self.igtm_client,
            partition=self.partition,
            gtm_server=self.gtm_server,
            record_type=self.record_type,
            virtual_server_config=virtual_server_config,
            pool_config=pool_config,
            pool_member_config=pool_member_config,
            wip_config=wip_config,
        )

        self.assertTrue(vs_mock.assert_called)
        self.assertTrue(pool_mock.assert_called)
        self.assertTrue(pool_member_mock.assert_called)
        self.assertTrue(wip_mock.assert_called)

    @patch('bigip_plugin.bigip_gtm._delete_virtual_servers')
    @patch('bigip_plugin.bigip_gtm._delete_server_pool')
    @patch('bigip_plugin.bigip_gtm._delete_wip')
    def test_delete_dns_loadbalancer(self, wip_mock, pool_mock, vs_mock):
        _ctx = self._prepare_loadbalancer_node()
        bigip_gtm.delete_dns_loadbalancer(ctx=_ctx, igtm=self.igtm_client,)

        self.assertTrue(wip_mock.assert_called)
        self.assertTrue(pool_mock.assert_called)
        self.assertTrue(vs_mock.assert_called)
