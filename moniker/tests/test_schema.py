# Copyright 2012 Managed I.T.
#
# Author: Kiall Mac Innes <kiall@managedit.ie>
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
from datetime import datetime
from moniker.tests import TestCase
from moniker import schema


class TestSchemaValidator(TestCase):
    def test_validate_format_hostname(self):
        test_schema = {
            "properties": {
                "hostname": {
                    "type": "string",
                    "format": "host-name",
                    "required": True
                },
            }
        }

        validator = schema.SchemaValidator(test_schema)

        valid_hostnames = [
            'example.com.',
            'www.example.com.',
            '12345.example.com.',
            '192-0-2-1.example.com.',
            'ip192-0-2-1.example.com.',
            'www.ip192-0-2-1.example.com.',
            'ip192-0-2-1.www.example.com.',
            'abc-123.example.com.',
            '_tcp.example.com.',
            '_service._tcp.example.com.',
            ('1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.8.b.d.0.1.0.0.2'
             '.ip6.arpa.'),
            '1.1.1.1.in-addr.arpa.',
        ]

        for hostname in valid_hostnames:
            validator.validate({'hostname': hostname})

    def test_validate_format_datetime(self):
        test_schema = {
            "properties": {
                "date_time": {
                    "type": "string",
                    "format": "date-time",
                    "required": True
                },
            }
        }

        validator = schema.SchemaValidator(test_schema)

        valid_datetimes = [
            datetime(2013, 1, 1)
        ]

        for dt in valid_datetimes:
            validator.validate({'date_time': dt})


class TestSchema(TestCase):
    def test_constructor(self):
        domain = schema.Schema('v1', 'domain')

        self.assertIsInstance(domain, schema.Schema)