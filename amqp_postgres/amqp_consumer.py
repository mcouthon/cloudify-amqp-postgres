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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############
import ssl
import json
import time
import logging

import pika
from pika.exceptions import AMQPConnectionError

logging.basicConfig()
logger = logging.getLogger('amqp_postgres')

D_CONN_ATTEMPTS = 12
D_RETRY_DELAY = 5


class AMQPTopicConsumer(object):

    def __init__(self,
                 exchange,
                 routing_key,
                 message_processor,
                 connection_parameters=None):
        """
            AMQPTopicConsumer initialisation expects a connection_parameters
            dict as provided by the __main__ of amqp_influx.
        """
        if connection_parameters is None:
            connection_parameters = {}

        self.message_processor = message_processor

        credentials = connection_parameters.get('credentials', {})
        credentials_object = pika.credentials.PlainCredentials(
            # These may be passed as None, so handle the default outside of
            # the get
            username=credentials.get('username') or 'guest',
            password=credentials.get('password') or 'guest',
        )
        connection_parameters['credentials'] = credentials_object

        if connection_parameters.get('ssl', False):
            connection_parameters['ssl_options'] = {
                'cert_reqs': ssl.CERT_REQUIRED,
                # Currently, not having a ca path with SSL enabled is
                # effectively an error, so we will let it fail
                'ca_certs': connection_parameters['ca_path'],
            }

        if 'ca_path' in connection_parameters.keys():
            # We don't need this any more
            connection_parameters.pop('ca_path')

        # add retry with try/catch because Pika currently ignoring these
        # connection parameters when using BlockingConnection:
        # https://github.com/pika/pika/issues/354
        attempts = connection_parameters.get('connection_attempts',
                                             D_CONN_ATTEMPTS)
        timeout = connection_parameters.get('retry_delay', D_RETRY_DELAY)
        for _ in range(attempts):
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(**connection_parameters))
            except AMQPConnectionError:
                time.sleep(timeout)
            else:
                break
        else:
            raise AMQPConnectionError

        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=exchange,
                                      type='topic',
                                      durable=False,
                                      auto_delete=True,
                                      internal=False)
        result = self.channel.queue_declare(
            auto_delete=True,
            durable=False,
            exclusive=False)
        queue = result.method.queue
        self.channel.queue_bind(exchange=exchange,
                                queue=queue,
                                routing_key=routing_key)
        self.channel.basic_consume(self._process,
                                   queue,
                                   no_ack=True)

    def consume(self):
        self.channel.start_consuming()

    def _process(self, channel, method, properties, body):
        try:
            parsed_body = json.loads(body)
            self.message_processor(parsed_body)
        except Exception as e:
            logger.warn('Failed message processing: {0}'.format(e))
