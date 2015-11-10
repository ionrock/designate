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
import socket

import mock

from designate.zone_manager import alias
from designate import exceptions


class TestALIASRecordFlattener(unittest.TestCase):

    def setUp(self):
        self.context = mock.Mock()
        self.central_api = mock.Mock()
        self.zone_id = 1234
        self.recordset = mock.Mock()
        self.storage = mock.Mock()

        self.flattener = alias.ALIASRecordFlattener(
            self.context,
            self.central_api,
            self.zone_id,
            self.recordset,
            self.storage
        )

    def test_init_allows_managed_records(self):
        assert self.context.edit_managed_records is True

    def test_get_record_obj(self):
        self.flattener.get_record_obj(1234)
        self.storage.get_record.assert_called_with(self.context, 1234)

    @mock.patch.object(alias, 'dns')
    def test_find_record_target_ips_success(self, dns):
        result = self.flattener.find_record_target_ips('foo.com.')
        dns.resolver.query.assert_called_with('foo.com.', 'A')
        assert result == [r.address for r in dns.resolver.query()]

    @mock.patch.object(alias, 'dns')
    def test_find_record_target_ips_nxdomain(self, dns):
        dns.resolver.query.side_effect = [dns.resolver.NXDOMAIN]
        result = self.flattener.find_record_target_ips('foo.com.')
        assert result == []

    @mock.patch.object(alias, 'dns')
    def test_find_record_target_ips_socket_error(self, dns):
        dns.resolver.query.side_effect = [socket.gaierror]
        result = self.flattener.find_record_target_ips('foo.com.')
        assert result == []

    def test_create_recordlist_from_record(self):
        alias_record = mock.Mock(data='foo.com.', id='1234')
        self.flattener.find_record_target_ips = mock.Mock()
        self.flattener.find_record_target_ips.return_value = [
            '192.168.1.1', '192.168.1.2'
        ]
        a_records = self.flattener.create_recordlist_from_record(alias_record)
        assert len(a_records) == 2

        assert a_records[0].data == '192.168.1.1'
        assert a_records[1].data == '192.168.1.2'

        assert a_records[0].managed
        assert a_records[0].managed_resource_type == 'ALIAS'
        assert a_records[0].managed_resource_id == '1234'

    @mock.patch.object(alias, 'objects')
    def test_update_recordset(self, objects):
        alias_record = mock.Mock(
            data='foo.com.',
            id='1234',
            name='foo zone',
        )
        self.flattener.find_record_target_ips = mock.Mock()
        self.flattener.find_record_target_ips.return_value = [
            '192.168.1.1', '192.168.1.2'
        ]

        self.flattener.create_recordset(alias_record)

        records = self.flattener.create_recordlist_from_record(alias_record)
        objects.RecordSet.assert_called_with(
            name=self.recordset.name,
            type='A',
            # TODO(elarson): This ttl should be from the upstream A
            #                record(s)
            ttl=3600,
            records=records,
            visible='mdns'
        )

        self.central_api.create_recordset.assert_called_with(
            self.context, self.zone_id, objects.RecordSet()
        )

    def test_existing_recordset_found(self):
        result = self.flattener.existing_recordset()
        assert result

        self.central_api.find_recordset.assert_called_with(
            self.context, criterion={
                'zone_id': self.zone_id, 'type': 'A'
            }
        )

    def test_existing_recordset_not_found(self):
        not_found = exceptions.RecordSetNotFound()
        self.central_api.find_recordset.side_effect = not_found
        result = self.flattener.existing_recordset()
        assert result is None

    def test_find_serial(self):
        serial = self.flattener.find_serial()
        self.central_api.get_zone.assert_called_with(
            self.context, self.zone_id
        )

        assert serial == self.central_api.get_zone().serial

    def test_flatten_record_create(self):
        self.flattener.existing_recordset = mock.Mock(return_value=None)
        self.flattener.create_recordset = mock.Mock()
        self.flattener.flatten_record('foo')

        self.flattener.create_recordset.assert_called_with('foo')

    def test_flatten_record_update(self):
        self.flattener.existing_recordset = mock.Mock(return_value='original')
        self.flattener.update_recordset = mock.Mock()
        self.flattener.flatten_record('foo')

        self.flattener.update_recordset.assert_called_with('original', 'foo')

    def test_flatten(self):
        record = mock.Mock(name='foo.com', data='bar.com.')
        self.recordset.records = [record]
        self.flattener.flatten_record = mock.Mock()

        self.flattener.flatten()

        self.flattener.flatten_record.assert_called_with(record)

    def test_delete(self):
        recordset = mock.Mock()
        self.flattener.existing_recordset = mock.Mock(
            return_value=recordset
        )
        self.flattener.delete()

        self.central_api.delete_recordset.assert_called_with(
            self.context, self.zone_id, recordset.id
        )

    def test_delete_noop_when_not_exists(self):
        self.flattener.existing_recordset = mock.Mock(return_value=None)

        self.flattener.delete()

        assert not self.central_api.delete_recordset.called


class TestALIASEntryFunctions(unittest.TestCase):

    @mock.patch.object(alias, 'ALIASRecordFlattener')
    def test_flatten(self, flattener_class):
        alias.flatten('foo')

        # Ensure we pass though *args
        flattener_class.assert_called_with('foo')
        assert flattener_class().flatten.called

    @mock.patch.object(alias, 'ALIASRecordFlattener')
    def test_delete(self, flattener_class):
        alias.delete('foo')

        # Ensure we pass though *args
        flattener_class.assert_called_with('foo')
        assert flattener_class().delete.called
