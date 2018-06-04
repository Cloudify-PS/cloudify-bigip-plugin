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
import logging
import json

# Third Party Imports
import requests
from requests.auth import HTTPBasicAuth

# local Imports
from . import LOGGER_NAME
from .decorators import handle_response

log = logging.getLogger(LOGGER_NAME)

BASE_URL = "https://{0}/mgmt/tm/gtm/{1}"

GTM_HEADERS = {
    'Content-Type': 'application/json',
    'Cache-Control': "no-cache"
}


class GTM(object):
    def __init__(self, ip=None, user=None, password=None, verify=False):
        self.ip = ip
        self.user = user
        self.password = password
        self.verify = verify
        self.auth = HTTPBasicAuth(self.user, self.password)

    def get_server(self, server=None):
        if server is None:
            uri = "server"
            return self._get(uri)
        else:
            uri = "server/{}".format(server)
            return self._get(uri)

    def add_vs(self, partition, server, payload):
        uri = "server/~{0}~{1}/virtual-servers".format(partition, server)
        return self._post(uri, payload)

    def list_vs(self, partition, server):
        uri = "server/~{0}~{1}/virtual-servers".format(partition, server)
        return self._get(uri)

    def delete_vs(self, partition, server, object_name):
        uri = "server/~{0}~{1}/virtual-servers/~{0}~{2}".format(
            partition, server, object_name)
        return self._delete(uri)

    def create_pool(self, record_type, payload):
        uri = "pool/{0}".format(record_type)
        return self._post(uri, payload)

    def delete_pool(self, partition, record_type, object_name):
        uri = "pool/{1}/~{0}~{2}".format(partition, record_type, object_name)
        return self._delete(uri)

    def add_pool_members(self, partition, record_type, object_name, payload):
        uri = "pool/{1}/~{0}~{2}/members".format(
            partition, record_type, object_name)

        return self._post(uri, payload)

    def create_wip(self, record_type, payload):
        uri = "wideip/{0}".format(record_type)
        return self._post(uri, payload)

    def delete_wip(self, partition, record_type, object_name):
        uri = "wideip/{1}/~{0}~{2}".format(partition, record_type, object_name)
        return self._delete(uri)

    @handle_response
    def _get(self, uri):
        url = BASE_URL.format(self.ip, uri)
        return requests.get(url=url, headers=GTM_HEADERS,
                            auth=self.auth, verify=self.verify)

    @handle_response
    def _delete(self, uri):
        url = BASE_URL.format(self.ip, uri)
        return requests.delete(url=url, headers=GTM_HEADERS,
                               auth=self.auth, verify=self.verify)

    @handle_response
    def _post(self, uri, payload=None):
        url = BASE_URL.format(self.ip, uri)

        post_request = dict()
        post_request['url'] = url
        post_request['headers'] = GTM_HEADERS
        post_request['auth'] = self.auth
        post_request['verify'] = self.verify

        if payload:
            post_request['data'] = json.dumps(payload)

        return requests.post(**post_request)
