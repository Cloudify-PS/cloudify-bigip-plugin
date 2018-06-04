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
import json

# Third Party Imports
import requests.exceptions

# local Imports
from .exceptions import GTMAPIException
from .exceptions import GTMConnectionErrorException


def handle_response(func):
    def wrapper(*args, **kwargs):
        url = args[1]
        try:
            response = func(*args, **kwargs)
        except requests.exceptions.RequestException as request_error:
            raise GTMConnectionErrorException(
                'Failed to call {0}'
                ' api with the following http response {1}'
                ''.format(url, request_error.response))

        # Get the status code
        status_code = response.status_code
        response_body = {}
        # Check if there response has content
        if response.text:
            response_body = json.loads(response.text)

        # Check the status code
        if status_code != 200:
            error_message = 'Error Status Code: {0}'.format(status_code)
            if response_body:
                error_message = '{0} , Error Message : {1}'.format(
                    error_message, response_body)
            raise GTMAPIException(error_message)
        return response_body

    return wrapper
