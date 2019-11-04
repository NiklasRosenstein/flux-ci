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
from . import BuildNotRunningError, BuildData, BuildManager
from ..process_manager import ProcessConfiguration, ProcessEventSink, ProcessManager
from ...models import orm, Build
from ... import config
import json
import nr.fs
import logging
import threading
import sys

runner_args = [sys.executable, '-m', __name__.rpartition('.')[0] + '.host_runner']


@implements(BuildManager, ProcessEventSink)
class HostBuildManager(object):

  def __init__(self, cancel_builds_on_shutdown=True):
    self._logger = logging.getLogger(__name__ + '.HostBuildManager')
    self._process_manager = ProcessManager(self, default_poll_interval=1)
    self._lock = threading.Lock()
    self._build_clients = {}
    self._cancel_builds_on_shutdown = cancel_builds_on_shutdown

  def init(self):
    self._logger.info('Starting process manager.')
    self._process_manager.start()

  def shutdown(self):
    # TODO (@NiklasRosenstein): Cancel running processes?
    self._logger.info('Stopping process manager.')
    self._process_manager.stop(
      terminate_processes=self._cancel_builds_on_shutdown)

  def start_build(self, build_data, build_client):  # type: (BuildData)
    self._logger.info('Starting build {}.'.format(build_data.build_id))

    # Read the build information.
    with orm.db_session:
      build = Build[build_data.build_id]
      build_path = build.path()
      build_scripts = config.build_scripts
      logfile = build.path(build.Data_Log)
      del build

    # Ensure that the log file directory exists.
    nr.fs.makedirs(nr.fs.dir(logfile))

    # Build the process configuration.
    command = runner_args + [build_path] + build_scripts
    process_config = ProcessConfiguration(command,
      stdout=open(logfile, 'wb'), stdin='pipe', stderr='stdout')

    # Create the process and send the build data via stdin.
    process = self._process_manager.start_process(build_data.build_id, process_config)
    process.stdin.write(json.dumps(build_data.to_json()).encode())
    process.stdin.write(b'\n')
    process.stdin.flush()

    with self._lock:
      self._build_clients[build_data.build_id] = build_client

  def cancel_build(self, build_id, build_client):  # type: (int)
    try:
      self._process_manager.terminate_process(build_id)
    except ValueError:
      raise BuildNotRunningError(build_id)
    build_client.set_status(build_id, Build.Status_Stopped)
    with self._lock:
      del self._build_clients[build_id]

  def process_finished(self, build_id, process):
    with self._lock:
      build_client = self._build_clients.pop(build_id, None)
    if build_client:  # May not be set if the build has been cancelled.
      build_client.set_status(build_id, Build.Status_Success
        if process.returncode == 0 else Build.Status_Error)
