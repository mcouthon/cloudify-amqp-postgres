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

import logging

import psycopg2

logging.basicConfig()
logger = logging.getLogger('amqp_postgres.publisher')


class PostgreSQLPublisher(object):
    def __init__(self, host, db, user, password):
        self._host = host
        self._db = db
        self._user = user
        self._password = password
        self._connection = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def _close(self):
        if self._connection is not None:
            self._connection.close()

    def _connect(self):
        self._connection = psycopg2.connect(
            database=self._db,
            user=self._user,
            host=self._host,
            password=self._password
        )

    def process(self, message, exchange):
        if exchange == 'cloudify-events':
            sql, args = self._get_events_sql(message)
        elif exchange == 'cloudify-logs':
            sql, args = self._get_logs_sql(message)
        else:
            raise StandardError('Unknown exchange type: {0}'.format(exchange))

        with self._connection.cursor() as cur:
            logger.error('Executing SQL statement: {0}'.format(sql))
            cur.execute(sql, args)
            logger.error('Status: {0}'.format(cur.statusmessage))
        self._connection.commit()

    @staticmethod
    def _get_logs_sql(message):
        sql = (
            "INSERT INTO logs ("
              "timestamp, "
              "reported_timestamp, "
              "_execution_fk, "
              "_tenant_id, "
              " _creator_id, "
              "logger, "
              "level, "
              "message, "
              "message_code, "
              "operation, "
              "node_id) "
            "SELECT "
              "now(), "
              "%s, "
              "_storage_id, "
              "_tenant_id, "
              "_creator_id, "
              "%s, "
              "%s, "
              "%s, "
              "NULL, "
              "%s, "
              "%s "
            "FROM executions WHERE id = %s;"
        )
        args = (
            message['timestamp'],
            message['logger'],
            message['level'],
            message['message']['text'],
            message['context'].get('operation'),
            message['context'].get('node_id'),
            message['context']['execution_id']
        )
        return sql, args

    @staticmethod
    def _get_events_sql(message):
        sql = (
            "INSERT INTO events ("
              "timestamp, "
              "reported_timestamp, "
              "_execution_fk, "
              "_tenant_id, "
              "_creator_id, "
              "event_type, "
              "message, "
              "message_code, "
              "operation, "
              "node_id, "
              "error_causes) "
            "SELECT "
              "now(), "
              "%s, "
              "_storage_id, "
              "_tenant_id, "
              "_creator_id, "
              "%s, "
              "%s, "
              "NULL, "
              "%s, "
              "%s, "
              "%s "
            "FROM executions WHERE id = %s;"
        )
        args = (
            message['timestamp'],
            message['event_type'],
            message['message']['text'],
            message['context'].get('operation'),
            message['context'].get('node_id'),
            message['context'].get('task_error_causes'),
            message['context']['execution_id']
        )

        return sql, args
