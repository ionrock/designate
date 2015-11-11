# Copyright (c) 2015 Rackspace Hosting
#
# Author: Eric Larson <eric.larson@rackspace.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import unittest

import mock

from designate.central import service
from designate import exceptions


class TestService(unittest.TestCase):

    def setUp(self):
        self.storage = mock.Mock()
        self.zone = mock.Mock(
            id=1234,
            name='foo.com.',
            type='PRIMARY',
            tenant_id='1001'
        )
        self.storage.get_zone.return_value = self.zone

        self.quota = mock.Mock()
        self.network_api = mock.Mock()
        self.pool_manager_api = mock.Mock()
        self.zone_manager_api = mock.Mock()

        # Short circuit the locking
        with mock.patch.object(service, 'synchronized_zone', lambda x: x):
            self.central = service.Service()
            self.central._pool_manager_api = self.pool_manager_api
            self.central._zone_manager_api = self.zone_manager_api
            self.central._network_api = self.network_api
            self.central._quota = self.quota
            self.central._storage = self.storage

            # Short circuit notifications
            self.central.notifier = mock.Mock()

    def test_constructor(self):
        assert self.central
        assert self.central.network_api == self.network_api
        assert self.central.quota == self.quota
        assert self.central.storage == self.storage

        # This is a dynamic property
        assert self.central.pool_manager_api == self.pool_manager_api
        assert self.central.zone_manager_api == self.zone_manager_api

    @mock.patch.object(service, 'policy')
    def test_create_recordset(self, policy):
        context = {}
        recordset = mock.Mock(
            name='bar', type='A', records=['10.0.0.1']
        )

        # This method does the real work
        self.central._create_recordset_in_storage = mock.Mock(
            return_value=(recordset, self.zone)
        )

        # create the actual recordset
        self.central.create_recordset(context, self.zone.id, recordset)

        assert policy.check.called
        # We assert the zone mock is passed, which asserts we called
        # storage.get_zone
        self.pool_manager_api.update_zone.assert_called_with(
            context, self.zone
        )

    def test_create_recordset_created_during_delete_is_error(self):
        context = {}
        recordset = mock.Mock(
            name='bar', type='A', records=['10.0.0.1']
        )
        self.zone.action = 'DELETE'

        # create the actual recordset
        self.assertRaises(exceptions.BadRequest,
                          self.central.create_recordset,
                          context, self.zone.id, recordset)

    @mock.patch.object(service, 'policy')
    def test_create_recordset_flatten_alias(self, policy):
        context = {}
        recordset = mock.Mock(
            name='bar', type='ALIAS', records=['example.com.']
        )

        self.central._create_recordset = mock.Mock()

        # This method does the real work
        self.central._create_recordset_in_storage = mock.Mock(
            return_value=(recordset, self.zone)
        )

        self.central.create_recordset(context, self.zone.id, recordset)

        self.zone_manager_api.flatten_alias_record.assert_called_with(
            context, self.zone.id, recordset
        )
