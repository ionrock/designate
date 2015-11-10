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
import socket

import dns.resolver
from oslo_log import log as logging
from oslo_config import cfg

from designate import objects
from designate import storage
from designate import exceptions
from designate.i18n import _LI

LOG = logging.getLogger(__name__)


class ALIASRecordFlattener(object):
    """
    Flatten any ALIAS records for a zone to an A record.
    """

    def __init__(self, context, central_api, zone_id, recordset,
                 storage_obj=None):
        self.context = context
        self.context.edit_managed_records = True

        # Use the default zone manager storage if we don't receive a
        # storage object.
        if not storage_obj:
            storage_driver = cfg.CONF['service:zone_manager'].storage_driver
            storage_obj = storage.get_storage(storage_driver)

        self.storage = storage_obj

        self.central_api = central_api
        self.zone_id = zone_id
        self.recordset = recordset

    def get_record_obj(self, record_id):
        """Get our record object from storage"""
        self.storage.get_record(self.context, record_id)

    def find_record_target_ips(self, endpoint):
        """Find the IP address of the ALIAS record hostname"""
        try:
            records = dns.resolver.query(endpoint, 'A')
            return [record.address for record in records]
        except (socket.gaierror, dns.resolver.NXDOMAIN):
            return []

    def create_recordlist_from_record(self, record):
        records = objects.RecordList()
        ips = self.find_record_target_ips(record.data)
        for ip in ips:
            records.append(objects.Record(
                data=ip,
                managed=1,
                managed_resource_type='ALIAS',
                managed_resource_id=record.id,
            ))

        return records

    def update_recordset(self, recordset, record):
        """Update an A recordset's IPs"""
        recordset.records = self.create_recordlist_from_record(record)

        LOG.info(_LI('Updating recordset: %s'), recordset)
        return self.central_api.update_recordset(self.context, recordset)

    def create_recordset(self, record):
        """Create a new A recordset from a list of IPs"""

        recordset = objects.RecordSet(
            name=self.recordset.name,
            type='A',
            ttl=3600,
            records=self.create_recordlist_from_record(record),
            visible='mdns'
        )

        LOG.info(_LI('Creating A Recordset: %s'), recordset)
        return self.central_api.create_recordset(
            self.context,
            self.zone_id,
            recordset
        )

    def existing_recordset(self):
        """Find the existing A recordset for an ALIAS record"""
        criterion = {
            'zone_id': self.zone_id,
            'type': 'A',
        }
        try:
            return self.central_api.find_recordset(
                self.context, criterion=criterion
            )
        except exceptions.RecordSetNotFound:
            return None

    def find_serial(self):
        zone = self.central_api.get_zone(
            self.context, self.zone_id
        )
        return zone.serial

    def flatten_record(self, record):
        orig_recordset = self.existing_recordset()
        if orig_recordset:
            return self.update_recordset(orig_recordset, record)
        return self.create_recordset(record)

    def flatten(self):
        """Flatten the ALIAS record

        This will create or update the necessary A records.
        """
        for record in self.recordset.records:
            LOG.info(_LI('Flattening: %(old)s to %(new)s'),
                     {'old': self.recordset.name, 'new': record.data})
            self.flatten_record(record)

    def delete(self):
        existing = self.existing_recordset()
        if existing:
            return self.central_api.delete_recordset(
                self.context,
                self.zone_id,
                existing.id
            )
        return True


def flatten(*args):
    """Flatten an ALIAS record"""
    flattener = ALIASRecordFlattener(*args)
    return flattener.flatten()


def delete(*args):
    flattener = ALIASRecordFlattener(*args)
    return flattener.delete()
