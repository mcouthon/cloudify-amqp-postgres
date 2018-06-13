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
import time
import unittest
import threading
from uuid import uuid4
from datetime import datetime

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
                # Expected to be a string, because usually from the shell
                amqp_ssl_enabled='false',
                amqp_ca_cert_path='',
                postgres_hostname='localhost',
                postgres_db='cloudify_db',
                postgres_user='cloudify',
                postgres_password='cloudify'

            )
        self.events_publisher = self._create_events_publisher()
        self._thread = None
        self._postgres_connection = self._get_postgres_connection()

    def tearDown(self):
        self.events_publisher.close()
        if self._postgres_connection:
            self._postgres_connection.close()

    def _get_postgres_connection(self):
        return psycopg2.connect(
            database=self.args.postgres_db,
            user=self.args.postgres_user,
            host=self.args.postgres_hostname,
            password=self.args.postgres_password
        )

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

        execution_id = str(uuid4())

        self._create_execution(execution_id)

        log = self._get_log(execution_id)
        event = self._get_event(execution_id)

        self.events_publisher.publish_message(log, message_type='log')
        self.events_publisher.publish_message(event, message_type='event')

        self._thread.join(3)

        db_log = self._get_db_log()
        db_event = self._get_db_event()

        self._assert_log(log, db_log)
        self._assert_event(event, db_event)

    def _create_execution(self, execution_id):
        sql = (
            'INSERT into executions('
            'id, _storage_id, _creator_id, _tenant_id'
            ') VALUES(%s, 0, 0, 0);'
        )
        with self._postgres_connection.cursor() as cur:
            cur.execute(sql, (execution_id, ))
        self._postgres_connection.commit()

    def _get_db_element(self, sql):
        with self._postgres_connection.cursor() as cur:
            cur.execute(sql)

            # Expecting only a single event in the table
            self.assertEqual(cur.rowcount, 1)

            return cur.fetchone()

    def _get_db_log(self):
        sql = 'SELECT id, timestamp, message, message_code, ' \
              'logger, level, operation, node_id, _execution_fk, ' \
              '_creator_id, _tenant_id, reported_timestamp, ' \
              'private_resource, visibility FROM logs;'
        return self._get_db_element(sql)

    def _get_db_event(self):
        sql = 'SELECT id, timestamp, message, message_code, ' \
              'event_type, error_causes, operation, node_id, _execution_fk, ' \
              '_creator_id, _tenant_id, reported_timestamp, ' \
              'private_resource, visibility FROM events;'
        return self._get_db_element(sql)

    def _assert_log(self, log, db_log):
        self.assertEqual(len(db_log), 14)

        self.assertEqual(db_log[0], None)  # id
        self.assertEqual(type(db_log[1]), datetime)  # timestamp
        self.assertEqual(db_log[2], log['message']['text'])  # message
        self.assertEqual(db_log[3], None)  # message code
        self.assertEqual(db_log[4], log['logger'])  # logger
        self.assertEqual(db_log[5], log['level'])  # level
        self.assertEqual(db_log[6], log['context']['operation'])  # operation
        self.assertEqual(db_log[7], log['context']['node_id'])  # node_id
        self.assertEqual(db_log[8], log['context']['execution_id'])  # exec_id
        self.assertEqual(db_log[9], 0)  # creator_id
        self.assertEqual(db_log[10], 0)  # tenant_id
        self.assertEqual(db_log[11], log['timestamp'])  # reported_timestamp
        self.assertEqual(db_log[12], None)  # private_resource
        self.assertEqual(db_log[13], None)  # visibility

    def _assert_event(self, event, db_event):
        self.assertEqual(len(db_event), 14)

        self.assertEqual(db_event[0], None)  # id
        self.assertEqual(type(db_event[1]), datetime)  # timestamp
        self.assertEqual(db_event[2], event['message']['text'])  # message
        self.assertEqual(db_event[3], None)  # message code
        self.assertEqual(db_event[4], event['event_type'])  # event_type
        self.assertEqual(db_event[5], None)  # error_causes
        self.assertEqual(db_event[6], None)  # operation
        self.assertEqual(db_event[7], None)  # node_id
        self.assertEqual(db_event[8], event['context']['execution_id'])
        self.assertEqual(db_event[9], 0)  # creator_id
        self.assertEqual(db_event[10], 0)  # tenant_id
        self.assertEqual(db_event[11], event['timestamp'])  # reported_ts
        self.assertEqual(db_event[12], None)  # private_resource
        self.assertEqual(db_event[13], None)  # visibility

    @staticmethod
    def now():
        return '{0}Z'.format(datetime.utcnow().isoformat()[:-3])

    def _get_log(self, execution_id):
        return {
            'context': {
                'blueprint_id': 'bp',
                'deployment_id': 'dep',
                'execution_id': execution_id,
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
            },
            'timestamp': self.now()
        }

    def _get_event(self, execution_id):
        return {
            'message': {
                'text': "Starting 'install' workflow execution",
                'arguments': None
            },
            'event_type': 'workflow_started',
            'context': {
                'deployment_id': 'dep',
                'workflow_id': 'install',
                'execution_id': execution_id,
                'blueprint_id': 'bp'
            },
            'timestamp': self.now()
        }
