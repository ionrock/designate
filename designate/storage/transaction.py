# Copyright 2015 Rackspace Hosting
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
import copy
import threading
import time

import wrapt
from oslo_utils import excutils
from oslo_log import log as logging
from oslo_db import exception as db_exception

from designate.i18n import _LW


LOG = logging.getLogger(__name__)

ENABLE_RETRIES = True
ENABLE_USE_TRANSACTION = True
ENABLE_TRANSACTION = True
RETRY_STATE = threading.local()


def _retry_on_deadlock(exc):
    """Filter to trigger retry a when a Deadlock is received."""
    # TODO(kiall): This is a total leak of the SQLA Driver, we'll need a better
    #              way to handle this.
    if isinstance(exc, db_exception.DBDeadlock):
        LOG.warning(_LW("Deadlock detected. Retrying..."))
        return True
    return False


def retry(cb=None, retries=50, delay=150):
    """A retry decorator that ignores attempts at creating nested retries.

    :param:retries: The number of retries
    :param:delay: Delay between tries in milliseconds
    """
    @wrapt.decorator(enabled=ENABLE_RETRIES)
    def retry_wrapper(wrapped, instance, args, kwargs):
        if not hasattr(RETRY_STATE, 'held'):
            # Create the state vars if necessary
            RETRY_STATE.held = False
            RETRY_STATE.retries = 0

        if not RETRY_STATE.held:
            # We're the outermost retry decorator
            RETRY_STATE.held = True

            try:
                while True:
                    try:
                        result = wrapped(*copy.deepcopy(args),
                                         **copy.deepcopy(kwargs))
                        break
                    except Exception as exc:
                        RETRY_STATE.retries += 1
                        if RETRY_STATE.retries >= retries:
                            # Exceeded retry attempts, raise.
                            raise
                        elif cb is not None and cb(exc) is False:
                            # We're not setup to retry on this exception.
                            raise
                        else:
                            # Retry, with a delay.
                            time.sleep(delay / float(1000))

            finally:
                RETRY_STATE.held = False
                RETRY_STATE.retries = 0

        else:
            # We're an inner retry decorator, just pass on through.
            result = wrapped(*copy.deepcopy(args),
                             **copy.deepcopy(kwargs))

        return result
    return retry_wrapper


@wrapt.decorator(enabled=ENABLE_USE_TRANSACTION)
def use_transaction(wrapped, instance, args, kwargs):
    instance.storage.begin()
    try:
        result = wrapped(*args, **kwargs)
        instance.storage.commit()
        return result
    except Exception:
        with excutils.save_and_reraise_exception():
            instance.storage.rollback()


@wrapt.decorator(enabled=ENABLE_TRANSACTION)
def transaction(wrapped, instance, args, kwargs):
    wrapped = use_transaction(wrapped)
    wrapped = retry(cb=_retry_on_deadlock)(wrapped)
    return wrapped(*args, **kwargs)
