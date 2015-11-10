# Copyright (c) 2015 Rackspace Hosting
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from designate.objects.record import Record
from designate.objects.record import RecordList


class ALIAS(Record):
    """
    ALIAS Resource Record

    An ALIAS record allows a top leve or apex record that points to
    another zone. This is soemtimes referred to as a top level CNAME
    Record. It is forbidden by the DNS RFC, yet implemented by many
    providers.
    """
    FIELDS = {
        'address': {
            'schema': {
                'type': 'string',
                'format': 'zonename',
                'maxLength': 255,
            },
            'required': True
        },
        'visible': {
            'schema': {
                'type': 'string',
                'enum': ['all', 'mdns', 'api'],
            }
        }
    }

    # Only show ALIAS records in the API
    visible = 'api'

    def _to_string(self):
        return self.address

    def _from_string(self, value):
        self.address = value

    # The record type is typically defined in the RFC, but as the RFC
    # explicitly forbids a top level CNAME, we'll go with PowerDNS'
    # code of 260.
    #
    #  https://github.com/PowerDNS/pdns/blob/5a1f298fd2816ce2c60fc001c05f149c8025ef7f/pdns/qtype.hh#L171
    RECORD_TYPE = 260


class ALIASList(RecordList):

    LIST_ITEM_TYPE = ALIAS
