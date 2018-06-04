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
import os
import uuid
from shutil import copyfile

from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause
from cloudify import cluster, constants

from bigip_sdk import bigip


@operation
def install_cert(key, cert, ctx):

    ip = ctx.node.properties['ip']
    user = ctx.node.properties['user']
    password = ctx.node.properties['password']
    name = ctx.node.properties['name']

    # save certs to file for http access
    base_path = "/opt/manager/resources/cloudify_agent"
    key_filename = str(uuid.uuid4()) + '.key'
    cert_filename = str(uuid.uuid4()) + '.crt'

    ctx.logger.info(
        'Generating key file {name} on manager'.format(name=key_filename)
    )
    _write_temp_file(os.path.join(base_path, key_filename), key)

    ctx.logger.info(
        'Generating cert file {name} on manager'.format(name=cert_filename)
    )
    _write_temp_file(os.path.join(base_path, cert_filename), cert)

    mgr_ip = _get_active_manager_ip(ctx)
    base_url = '{ip}:53229/cloudify_agent/{filename}'
    key_url = base_url.format(
        ip=mgr_ip,
        filename=key_filename
    )
    cert_url = base_url.format(
        ip=mgr_ip,
        filename=cert_filename
    )

    ctx.logger.info("Installing certificate {0} on BIG-IP={1}"
                    .format(name, ip))
    try:
        result = bigip.install_cert(ip,
                                    user,
                                    password,
                                    name,
                                    key_url,
                                    cert_url)

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

    finally:
        # remove temp files
        ctx.logger.info('Cleaning up cert and key files.')
        os.remove(os.path.join(base_path, key_filename))
        os.remove(os.path.join(base_path, cert_filename))

    for key, value in result.items():
        ctx.instance.runtime_properties[key] = value


@operation
def delete_cert(ctx):
    ip = ctx.node.properties['ip']
    user = ctx.node.properties['user']
    password = ctx.node.properties['password']

    key_name = ctx.instance.runtime_properties['key_name']
    cert_name = ctx.instance.runtime_properties['cert_name']

    ctx.logger.info(
        'Deleting key {key_name} and cert {cert_name} from '
        '{load_balancer}.'.format(
            key_name=key_name,
            cert_name=cert_name,
            load_balancer=ip,
        )
    )
    bigip.delete_cert(
        ip=ip,
        username=user,
        passwd=password,
        key_name=key_name,
        cert_name=cert_name,
    )
    ctx.logger.info(
        'Key {key_name} and cert {cert_name} have been deleted from '
        '{load_balancer}.'.format(
            key_name=key_name,
            cert_name=cert_name,
            load_balancer=ip,
        )
    )


def _get_active_manager_ip(ctx):
    if cluster.is_cluster_configured():
        active_node_ip = cluster.get_cluster_active()
        if active_node_ip:
            ctx.logger.debug("active node ip")
            return str(active_node_ip)[:-16]
    ctx.logger.debug("from OS active node ip")
    return str(os.environ[constants.MANAGER_FILE_SERVER_URL_KEY])[:-16]


def _write_temp_file(filename, source):
    if os.path.isfile(source):
        copyfile(source, filename)
    else:
        with open(filename, "w") as key_handle:
            key_handle.write(source)
