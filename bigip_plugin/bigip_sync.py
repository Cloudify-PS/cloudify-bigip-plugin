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

import sys

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause

from bigip_sdk import bigip


PARAMS_IP = "ip"
PARAMS_SYNC_GROUP = "sync_group"
PARAMS_USER = "user"
PARAMS_PASSWORD = "password"


@operation
def sync(sync_group,
         retry_timer,
         ctx):
    try:
        ip = ctx.node.properties['ip']
        user = ctx.node.properties['user']
        password = ctx.node.properties['password']

        ctx.logger.info("Syncing BIG IP: ip={0}, sync_group={1}"
                        .format(ip, sync_group))

        bigip.do_sync(ip, sync_group, user, password, retry_timer)
    except Exception as e:
        _, exc_value, exc_traceback = sys.exc_info()
        raise NonRecoverableError(
            "Failed to install certificate on {load_balancer}. "
            "{exception_type} {message}".format(
                load_balancer=ip,
                exception_type=type(e),
                message=e.message,
            ),
            causes=[exception_to_error_cause(exc_value, exc_traceback)]
        )
