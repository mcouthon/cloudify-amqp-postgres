########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
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

import os
import unittest
import threading
import time

from collections import namedtuple

import psycopg2

from cloudify.amqp_client import create_events_publisher

from amqp_postgres.__main__ import main


Args = namedtuple(
    'Args',
    'amqp_hostname '
    'amqp_username '
    'amqp_password '
    'amqp_ssl_enabled '
    'amqp_ca_cert_path '
    'postgres_hostname '
    'postgres_db '
    'postgres_user '
    'postgres_password '
)


class Test(unittest.TestCase):

    def setUp(self):
        self.args = Args(
                amqp_hostname='localhost',
                amqp_username='guest',
                amqp_password='guest',
                amqp_ssl_enabled=False,
                amqp_ca_cert_path='',
                postgres_hostname='localhost',
                postgres_db='cloudify',
                postgres_user='cloudify',
                postgres_password='cloudify'

            )
        self.events_publisher = self._create_events_publisher()
        self._thread = None

    def tearDown(self):
        self.events_publisher.close()

    def _create_events_publisher(self):
        os.environ['AGENT_NAME'] = 'test'
        return create_events_publisher(
            amqp_host=self.args.amqp_hostname,
            amqp_user=self.args.amqp_username,
            amqp_pass=self.args.amqp_password,
            amqp_vhost='/',
            ssl_enabled=False,
            ssl_cert_path=''
        )

    def _run_amqp_postgres(self):
        self._thread = threading.Thread(target=main, args=(self.args,))
        self._thread.daemon = True
        self._thread.start()

    def test(self):
        self._run_amqp_postgres()

        time.sleep(5)

        self._publish_event()
        self._publish_log()

        self._thread.join(3)

        self._assert_db_state()

    def _assert_db_state(self):
        pass

    def _publish_log(self):
        log = {
            'context': {
                'blueprint_id': 'bp',
                'deployment_id': 'dep',
                'execution_id': '1111',
                'node_id': 'vm_7j36my',
                'node_name': 'vm',
                'operation': 'cloudify.interfaces.cloudify_agent.create',
                'plugin': 'agent',
                'task_id': 'a13973d5-3866-4054-baa1-479e242fff75',
                'task_name': 'cloudify_agent.installer.operations.create',
                'task_queue': 'cloudify.management',
                'task_target': 'cloudify.management',
                'workflow_id': 'install'
            },
            'level': 'debug',
            'logger': 'ctx.a13973d5-3866-4054-baa1-479e242fff75',
            'message': {
                'text': 'Test log'
            }
        }

        self.events_publisher.publish_message(log, message_type='log')

    def _publish_event(self):
        event = {
            "message": {
                "text": "Starting 'create_deployment_environment' workflow execution",
                "arguments": None
            },
            "event_type": "workflow_started",
            "context": {
                "deployment_id": "dep",
                "workflow_id": "create_deployment_environment",
                "execution_id": "460f89fa-5626-41ca-9a7c-039b4a6040d7",
                "blueprint_id": "bp"
            }
        }

        self.events_publisher.publish_message(event, message_type='event')
