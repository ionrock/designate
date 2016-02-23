# Copyright 2016 Rackspace Hosting
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

from mock import Mock
from mock import patch

from designate.storage import transaction


class noop_decorator(object):
    def __init__(self, *args, **kw):
        self.args = args
        self.kw = kw

    def __call__(self, f):
        return f


class Foo(object):
    def __init__(self, results=None):
        self.storage = Mock()
        self.result = Mock()
        self.result.side_effect = results or ['foo']

    def foo(self):
        return self.result()


class TestTransaction(unittest.TestCase):

    @patch('designate.storage.transaction.retry', noop_decorator)
    def test_decorator(self):
        obj = Foo()
        f = transaction.transaction(obj.foo)
        assert f() == 'foo'

        assert obj.storage.begin.called
        assert obj.storage.commit.called

    @patch('designate.storage.transaction._retry_on_deadlock')
    def test_decorator_retries(self, retry_func):
        retry_func.return_value = True

        obj = Foo([Exception('db failure'), 'foo'])

        f = transaction.transaction(obj.foo)
        assert f() == 'foo'

        assert obj.storage.begin.called
        assert obj.storage.commit.called
        assert retry_func.called

    @patch('designate.storage.transaction._retry_on_deadlock')
    def test_manual_decoration(self, retry_func):
        retry_func.return_value = True

        class ManualDecorate(Foo):
            def run_doit_in_transaction(self):
                return transaction.transaction(self.foo)()

        foo = ManualDecorate([Exception('fail1'), 'foo'])
        assert foo.run_doit_in_transaction() == 'foo'

        assert foo.storage.begin.called
        assert foo.storage.commit.called
        assert retry_func.called

    @patch('designate.storage.transaction._retry_on_deadlock')
    def test_rollback_on_failure(self, retry_func):
        retry_func.return_value = False

        obj = Foo([Exception('db failure')])

        f = transaction.transaction(obj.foo)
        try:
            f()
        except Exception:
            assert True

        assert obj.storage.begin.called
        assert obj.storage.rollback.called
        assert retry_func.called
