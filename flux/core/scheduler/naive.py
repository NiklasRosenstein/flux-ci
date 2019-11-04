# Copyright (c) 2019  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from nr.types.interface import implements
from . import Scheduler
from ...models import orm, Build
from ...clients.local import LocalBuildClient
import logging
import threading
import time


@implements(Scheduler)
class NaiveScheduler(object):
  """ This scheduler implementation starts build as soon as it finds them
  queued in the database. """

  def __init__(self, poll_interval=1):
    self._logger = logging.getLogger(__name__ + '.NaiveScheduler')
    self._poll_interval = poll_interval
    self._build_manager = None
    self._thread = None
    self._stopped = None

  def init(self, build_manager):
    self._build_manager = build_manager
    self._logger.info('Starting.')
    self._stopped = threading.Event()
    self._thread = threading.Thread(target=self._run)
    self._thread.start()

  def shutdown(self):
    self._logger.info('Shutting down.')
    self._stopped.set()
    self._thread.join()

  def _run(self):
    while not self._stopped.is_set():
      with orm.db_session(optimistic=False):
        build = self._get_next_build()
        if build is not None:
          build.transition(Build.Status_Building)
          build_data = build.get_build_data()
          self._build_manager.start_build(build_data, LocalBuildClient())
          continue
      time.sleep(self._poll_interval)
    self._logger.info('Stopped.')

  def _get_next_build(self):
    return orm.select(x for x in Build if x.status == Build.Status_Queued).first()
