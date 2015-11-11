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
from oslo_log import log as logging
from sqlalchemy import Column, MetaData, Table, Enum
from migrate.changeset.constraint import UniqueConstraint

VISIBLE_TYPES = ['all', 'mdns', 'api']

LOG = logging.getLogger(__name__)

meta = MetaData()


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    meta.bind = migrate_engine
    recordsets_table = Table('recordsets', meta, autoload=True)

    dialect = migrate_engine.url.get_dialect().name
    using_sqlite = dialect.startswith('sqlite')

    if dialect.startswith('postgresql'):
        with migrate_engine.connect() as conn:
            conn.execution_options(isolation_level='AUTOCOMMIT')
            conn.execute(
                "ALTER TYPE recordset_types ADD VALUE 'ALIAS' "
                "AFTER 'SOA'")
            conn.close()

    if not dialect.startswith('sqlite'):
        # sqlite just uses a varchar instead, so we don't need to do
        # anything about it.
        type_col = recordsets_table.c.type
        record_types = list(type_col.type.enums)
        record_types.append('ALIAS')
        recordsets_table.c.type.alter(
            type=Enum(name='recordset_types', *record_types)
        )

    # Re-add constraint for sqlite
    if dialect.startswith('sqlite'):
        constraint = UniqueConstraint('zone_id', 'name', 'type',
                                      name='unique_recordset',
                                      table=recordsets_table)
        constraint.create()

    # Add visible column
    recordsets_visible_col = Column(
        'visible',
        Enum(name='visibility', *VISIBLE_TYPES),
        default='all',
        nullable=using_sqlite
    )
    recordsets_visible_col.create(recordsets_table)


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    recordsets_table = Table('recordsets', meta, autoload=True)
    recordsets_table.c.visible.drop()

    dialect = migrate_engine.url.get_dialect().name
    if not dialect.startswith('sqlite'):
        # Update our types column with ALIAS type
        recordset_types_col = recordsets_table.c.type
        record_types = list(recordset_types_col.enums)
        record_types.pop(record_types.index('ALIAS'))
        recordset_types_col.alter(
            type=Enum('record_types', *record_types)
        )
