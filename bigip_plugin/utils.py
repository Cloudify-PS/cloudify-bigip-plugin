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
import sys

# Third Party Imports
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError
from cloudify.exceptions import RecoverableError
from cloudify.utils import exception_to_error_cause

# local Imports
from bigip_sdk import gtm
from bigip_sdk import exceptions


GTM_PASSWORD = 'password'
GTM_USER = 'user'
GTM_IP = 'ip'

GTM_KEYS = (
    GTM_PASSWORD,
    GTM_USER,
    GTM_IP
)


def generate_traceback_exception():
    _, exc_value, exc_traceback = sys.exc_info()
    response = exception_to_error_cause(exc_value, exc_traceback)
    return response


def get_traceback_exception():
    error_traceback = generate_traceback_exception()
    error_message = 'Error traceback {0} with message' \
                    ' {1}'.format(error_traceback['traceback'],
                                  error_traceback['message'])
    ctx.logger.error(error_message)
    return error_traceback


def with_gtm_client(function):
    def wrapper(**kwargs):
        # This will fetch the properties of the GTM instance from the
        # relationship of the node
        try:
            gmt_prop = {k: ctx.node.properties[k] for k in GTM_KEYS}
            kwargs['igtm'] = gtm.GTM(**gmt_prop)
            function(**kwargs)
        except exceptions.GTMConnectionErrorException as connection_error:
            error_traceback = get_traceback_exception()
            raise RecoverableError(retry_after=30,
                                   message='{0}'.format(str(connection_error)),
                                   causes=error_traceback)
        except Exception as error:
            error_traceback = get_traceback_exception()
            raise NonRecoverableError('{0}'.format(str(error)),
                                      causes=[error_traceback])
    return wrapper
