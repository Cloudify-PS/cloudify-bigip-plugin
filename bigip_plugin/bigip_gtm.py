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


# Third Party Imports
from cloudify.decorators import operation
from cloudify.exceptions import NonRecoverableError

# local Imports
from . import utils


def _create_virtual_server(ctx, igtm, partition, gtm_server, resource_config):
    vs_name = resource_config.get('name')

    ctx.logger.info("Adding virtual server {0} to GTM Server {1}, "
                    "partition {2}".format(vs_name, gtm_server, partition))

    # Update the name of the virtual server
    resource_config['name'] = '/{0}/{1}'.format(partition, vs_name)
    response = igtm.add_vs(partition, gtm_server, resource_config)

    # Log created response
    ctx.logger.info("Adding virtual server {0}"
                    " created successfully {1}".format(vs_name, response))

    return response


def _get_existing_virtual_servers(igtm, partition, gtm_server):
    virtual_servers = igtm.list_vs(partition, gtm_server)
    existing_virtual_servers = virtual_servers.get('items')
    return existing_virtual_servers


def _generate_gtm_virtual_servers(ctx,
                                  igtm,
                                  partition,
                                  gtm_server,
                                  existing_virtual_servers,
                                  virtual_servers):

    # This list of all virtual servers added to the GTM servers as specified
    # by the inputs
    gmt_virtual_servers = []
    for virtual_server in virtual_servers:
        # Check if the new virtual server is already added to the GTM by
        # checking if they have the same the "destination" value, then this
        # will be marked as "IsAddedManually"
        existing_virtual_server = filter(
            lambda existing_server:
            virtual_server['destination'] == existing_server['destination'],
            existing_virtual_servers)

        if existing_virtual_server:
            existing_virtual_server[0]['IsAddedManually'] = False
            # This virtual server which already added, should not be
            # removed when running the "uninstall" workflow
            gmt_virtual_servers.append(existing_virtual_server[0])
            destination = existing_virtual_server[0]['destination']

            ctx.logger.warn("Virtual server destination {0} already exists"
                            .format(destination))

        else:
            # This should be added manually
            # Add the new virtual servers manually to the GTM servers
            # These virtual servers must be deleted when
            # "uninstall" workflow executed
            created_virtual_server = _create_virtual_server(ctx,
                                                            igtm,
                                                            partition,
                                                            gtm_server,
                                                            virtual_server)
            created_virtual_server['IsAddedManually'] = True
            gmt_virtual_servers.append(created_virtual_server)

    return gmt_virtual_servers


def _generate_pool_members(ctx, pool_members):
    virtual_servers = ctx.instance.runtime_properties.get('virtual_servers')
    # Check if there is an object called "virtual_servers" in order to check
    # which pool members should be added to the pool
    if not virtual_servers:
        raise NonRecoverableError('No virtual servers found')

    # If all the pool members added manually then, add all the
    # pool members as specified in "gtm_pool_member_config"
    if all(virtual_server['IsAddedManually']
           for virtual_server in virtual_servers):

        for pool_member in pool_members:
            pool_member['name'] = '/{0}/{1}'.format(pool_member['partition'],
                                                    pool_member['name'])

        return pool_members

    added_members = []

    # If the provided "gtm_pool_member_config" does not match all the
    # virtual_servers created then add to pools from  "virtual_servers"
    for index, virtual_server in enumerate(virtual_servers):
        pool_member = dict()
        pool_member['name'] = virtual_server['name']
        pool_member['memberOrder'] = index
        added_members.append(pool_member)

    return added_members


def _manage_multiple_virtual_servers(ctx, igtm, partition,
                                     gtm_server, virtual_servers):

    # Check if "GTM" has virtual servers associated with it before adding any
    # virtual servers in order to decide whether or not to add the virtual
    # servers provided via input file
    existing_virtual_servers = _get_existing_virtual_servers(igtm,
                                                             partition,
                                                             gtm_server)

    # Set required runtime properties to be used later on on the lifecycle
    # of the managing GSLB resources
    ctx.instance.runtime_properties['gtm_server'] = gtm_server
    ctx.instance.runtime_properties['partition'] = partition

    # Virtual servers input
    virtual_servers = virtual_servers.get('kwargs')
    gtm_virtual_servers =\
        _generate_gtm_virtual_servers(ctx,
                                      igtm,
                                      partition,
                                      gtm_server,
                                      existing_virtual_servers,
                                      virtual_servers)

    if gtm_virtual_servers:
        # Set runtime properties for gtm virtual servers instances
        ctx.instance.runtime_properties['virtual_servers']\
            = gtm_virtual_servers


def _delete_virtual_servers(ctx, igtm):
    virtual_servers = ctx.instance.runtime_properties.get('virtual_servers')
    # Check if there is an object called "virtual_servers" so that the
    # resources can be removed when running the un-install workflow
    if not virtual_servers:
        raise NonRecoverableError('No virtual servers found to delete')

    # Get the partition used to create the virtual servers
    partition = ctx.instance.runtime_properties.get('partition')
    server_name = ctx.instance.runtime_properties.get('gtm_server')

    for virtual_server in virtual_servers:
        # Only Remove virtual servers added manually
        if virtual_server.get('IsAddedManually'):
            # The format of the created virtual server wil
            # be like the following/PARTITION/VIRTUAL_SERVER_NAME/
            #  the required needed value is the VIRTUAL_SERVER_NAME
            vs_name = virtual_server.get('name').split('/')[2]
            ctx.logger.info(
                "Removing virtual server {0} from GTM server {1},"
                "partition {2}".format(vs_name, server_name, partition))

            igtm.delete_vs(partition, server_name, vs_name)

            # Log created response
            ctx.logger.info("Removing virtual server {0}"
                            " done successfully".format(vs_name))

    ctx.instance.runtime_properties.pop('virtual_servers')
    ctx.instance.runtime_properties.pop('partition')
    ctx.instance.runtime_properties.pop('gtm_server')


def _create_server_pool(ctx, igtm, record_type, resource_config):

    resource = resource_config.get('kwargs')
    partition = resource.get('partition')
    pool_name = resource.get('name')

    ctx.instance.runtime_properties['pool_name'] = pool_name
    ctx.instance.runtime_properties['record_type'] = record_type

    ctx.logger.info("Adding pool server {0}, "
                    "partition {1}".format(pool_name, partition))

    response = igtm.create_pool(record_type, resource)

    # Log created response
    ctx.logger.info("Adding pool server {0}"
                    " created successfully {1}".format(pool_name, response))

    # Set runtime properties for pool server instance response
    ctx.instance.runtime_properties['pool'] = response


def _delete_server_pool(ctx, igtm):
    partition = ctx.instance.runtime_properties.get('partition')
    pool_name = ctx.instance.runtime_properties.get('pool_name')
    record_type = ctx.instance.runtime_properties.get('record_type')

    ctx.logger.info("Removing pool server {0}, "
                    "partition {1}".format(pool_name, partition))

    igtm.delete_pool(partition, record_type, pool_name)

    # Log created response
    ctx.logger.info("Removing pool server {0}"
                    " done successfully".format(pool_name))

    ctx.instance.runtime_properties.pop('pool')
    ctx.instance.runtime_properties.pop('pool_members')
    ctx.instance.runtime_properties.pop('pool_name')
    ctx.instance.runtime_properties.pop('record_type')


def _add_pool_member(ctx, igtm, record_type, resource_config):
    pool_name = ctx.instance.runtime_properties.get('pool_name')
    member_name = resource_config.get('name')

    # Read partition either from "resource_config" or from "pool"
    # runtime properties object
    partition =\
        resource_config.get('partition') \
        or ctx.instance.runtime_properties.get('pool')['partition']

    ctx.logger.info("Adding virtual server {0} to pool {1}"
                    .format(member_name, pool_name))

    response = igtm.add_pool_members(partition, record_type,
                                     pool_name, resource_config)

    # Log created response
    ctx.logger.info("Adding virtual server {0} to pool"
                    " created successfully {1} {2}".
                    format(member_name, pool_name, response))

    return response


def _manage_pool_members(ctx, igtm, record_type, gtm_server, pool_members):
    pool_members = pool_members.get('kwargs')
    added_members = []
    pool_members = _generate_pool_members(ctx, pool_members)

    for pool_member in pool_members:
        pool_member['name'] = '{0}:{1}'.format(gtm_server, pool_member['name'])
        response = _add_pool_member(ctx, igtm, record_type, pool_member)
        added_members.append(response)

    if added_members:
        # Set runtime properties for added virtual pool members
        ctx.instance.runtime_properties['pool_members'] = added_members


def _create_wip(ctx, igtm, record_type, resource_config):
    resource = resource_config.get('kwargs')
    wip_name = resource.get('name')

    ctx.instance.runtime_properties['wip_name'] = wip_name
    ctx.logger.info("Adding wip ip {0}".format(wip_name))

    response = igtm.create_wip(record_type, resource)

    # Set runtime properties for wip instance response
    ctx.instance.runtime_properties['wip'] = response

    # Log created response
    ctx.logger.info("Creating wip ip {0} "
                    " done successfully {1}".
                    format(record_type, response))


def _delete_wip(ctx, igtm):
    partition = ctx.instance.runtime_properties.get('partition')
    wip_name = ctx.instance.runtime_properties.get('wip_name')
    record_type = ctx.instance.runtime_properties.get('record_type')

    ctx.logger.info("Removing wip ip server {0}, "
                    "partition {1}".format(wip_name, partition))

    igtm.delete_wip(partition, record_type, wip_name)

    # Log created response
    ctx.logger.info("Removing wip ip {0}"
                    " done successfully".format(wip_name))

    ctx.instance.runtime_properties.pop('wip')
    ctx.instance.runtime_properties.pop('wip_name')


@utils.with_gtm_client
@operation
def create_dns_loadbalancer(ctx,
                            igtm,
                            partition,
                            gtm_server,
                            record_type,
                            virtual_server_config,
                            pool_config,
                            pool_member_config,
                            wip_config):

    # Create multiple virtual servers

    virtual_servers = ctx.instance.runtime_properties.get('virtual_servers')
    # Create virtual servers only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and no "virtual_servers"
    # property exists
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and not virtual_servers):

        _manage_multiple_virtual_servers(ctx,
                                         igtm,
                                         partition,
                                         gtm_server,
                                         virtual_server_config)

    # Create server pool

    pool = ctx.instance.runtime_properties.get('pool')
    # Create pool only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and no "pool" property exists
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and not pool):
        _create_server_pool(ctx,
                            igtm,
                            record_type,
                            pool_config)

    # Add members to pool

    pool_members = ctx.instance.runtime_properties.get('pool_members')
    # Add pool members only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and no "pool_members"
    # property exists
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and not pool_members):
        _manage_pool_members(ctx, igtm,
                             record_type,
                             gtm_server,
                             pool_member_config)

    # Create wip

    wip = ctx.instance.runtime_properties.get('wip')
    # Add wip only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and no "wip"
    # property exists
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and not wip):

        _create_wip(ctx, igtm, record_type, wip_config)


@utils.with_gtm_client
@operation
def delete_dns_loadbalancer(ctx, igtm, **kwargs):

    # Delete wip

    wip = ctx.instance.runtime_properties.get('wip')
    # Delete wip only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and has "wip"
    # property exists
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and wip):

        _delete_wip(ctx, igtm)

    # Delete server pool

    pool = ctx.instance.runtime_properties.get('pool')
    # Delete pool only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and has "pool" property
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and pool):
        _delete_server_pool(ctx, igtm)

    # Delete virtual_server

    virtual_servers = ctx.instance.runtime_properties.get('virtual_servers')
    # Delete virtual servers only in the following cases:
    # - If this is the first operation run (ctx.operation.retry_number = 0)
    # - If operation retries multiple times and has "virtual_servers" property
    if ctx.operation.retry_number == 0 \
            or (ctx.operation.retry_number != 0 and virtual_servers):
        _delete_virtual_servers(ctx, igtm)
