# Copyright 2015 Rackspace Inc.
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

from designate.zone_manager import rpcapi


class TestZoneManagerAPI(unittest.TestCase):

    def setUp(self):
        self.ctx = {}
        self.zone_id = 1234
        self.recordset = mock.Mock()

        self.client = mock.Mock()
        self.api = rpcapi.ZoneManagerAPI(client=self.client)

    def test_contructor(self):
        assert self.api

    def test_flatten_alias_record(self):
        self.api.flatten_alias_record(self.ctx, self.zone_id, self.recordset)

        self.client.cast.assert_called_with(
            self.ctx, 'flatten_alias_record',
            zone_id=self.zone_id,
            recordset=self.recordset
        )

    def test_delete_alias_record(self):
        self.api.delete_alias_record(self.ctx, self.zone_id, self.recordset)

        self.client.cast.assert_called_with(
            self.ctx, 'delete_alias_record',
            zone_id=self.zone_id,
            recordset=self.recordset
        )
