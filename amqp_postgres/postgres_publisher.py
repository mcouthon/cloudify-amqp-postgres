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
logger = logging.getLogger('amqp_postgres')


class PostgreSQLPublisher(object):
    def __init__(self, host, db, user, password):
        self._host = host
        self._db = db
        self._user = user
        self._password = password
        self._connection = None
        self._cursor = None

    def __enter__(self):
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._close()

    def _close(self):
        if self._cursor is not None:
            self._cursor.close()

        if self._connection is not None:
            self._connection.close()

    def _connect(self):
        self._connection = psycopg2.connect(
            database=self._db,
            user=self._user,
            host=self._host,
            password=self._password
        )
        self._cursor = self._connection.cursor()

    def process(self, message):
        print('#' * 80)
        logger.error('#' * 80)
        print(message)
        logger.error(message)

        raise StandardError('here')
