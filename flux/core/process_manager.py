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

from functools import partial
from nr.types.interface import Interface

import collections
import heapq
import json
import logging
import os
import subprocess
import time
import threading


class ProcessEventSink(Interface):

  def process_finished(self, process_id, process):
    pass


class ProcessConfiguration(object):

  def __init__(self, command, stdout=None, stderr=None, stdin=None,
               cwd=None, env=None, inherit_environment=True):
    if stdin == 'pipe':
      stdin = subprocess.PIPE
    if stdout == 'pipe':
      stdout = subprocess.PIPE
    if stderr == 'stdout':
      stderr = subprocess.STDOUT
    elif stderr == 'pipe':
      stderr = subprocess.PIPE
    self.command = command
    self.stdout = stdout
    self.stderr = stderr
    self.stdin = stdin
    self.cwd = cwd
    self.env = env
    self.inherit_environment = inherit_environment

  def create(self):
    env = os.environ.copy() if self.inherit_environment else {}
    env.update(self.env or {})
    return subprocess.Popen(self.command, stdout=self.stdout,
      stderr=self.stderr, stdin=self.stdin, cwd=self.cwd, env=env)


class ProcessManager(object):
  """ The ProcessManager manages the lifecycle of a process and generates
  events when a process is created or finished. """

  _HeapItem = collections.namedtuple(
    'HeapItem', 'next_poll_time,poll_interval,process_id')

  def __init__(self, event_sink, default_poll_interval=10, time_provider=None):
    # type: (ProcessEventSink, int, Callable[[], float])
    self.event_sink = event_sink
    self.default_poll_interval = default_poll_interval
    self.time_provider = time_provider or getattr(time, 'perf_counter', time.clock)
    self._logger = logging.getLogger(__name__ + '.ProcessManager')
    self._processes = {}
    self._heap = []
    self._lock = threading.Lock()
    self._stop_event = None
    self._thread = None

  @property
  def started(self):
    return self._stop_event and not self._stop_event.is_set()

  def start(self, poll_threshold=0.01, wait_on_stop=True):
    """ Starts the process manager polling thread. If *wait_on_stop* is set
    to True (default) the #ProcessManager will keep polling until the last
    process has finished. """

    with self._lock:
      if self.started:
        raise RuntimeError('ProcessManager already started.')

    self._stop_event = threading.Event()
    func = partial(self._run, poll_threshold, wait_on_stop)
    self._thread = threading.Thread(target=func)
    self._thread.daemon = True
    self._thread.start()

  def stop(self, wait=True, terminate_processes=False):
    """ Stops the polling thread. If *terminate_processes* is set to True,
    all currently running processes are terminated before waiting for the
    background thread to finish. """

    with self._lock:
      if not self.started:
        raise RuntimeError('ProcessManager not started.')
      self._stop_event.set()
      if terminate_processes:
        for process in self._processes.values():
          process.terminate()
    if wait:
      self._thread.join()

  def start_process(self, process_id, process_config, poll_interval=None):
    # type: (str, ProcessConfiguration, Optional[int])
    """ Starts a new process. Raises a #RuntimeError if a process with the
    specified *process_id* already exists (until the process is removed after
    it finished). Raises a #ValueError if *poll_interval* is below 0.1 (100ms).

    May raise any exception that #ProcessConfiguration.create() raises.
    """

    if poll_interval is None:
      poll_interval = self.default_poll_interval
    if poll_interval < 0.1:
      raise ValueError('poll_interval must not be lower than 0.1')

    with self._lock:
      if not self.started:
        raise RuntimeError('ProcessManager is not started')
      if process_id in self._processes:
        raise RuntimeError('Process with ID {!r} already exists'
                           .format(process_id))
      process = self._processes[process_id] = process_config.create()
      self._requeue(process_id, poll_interval)
      self._logger.info('Process {!r} started.'.format(process_id))

    return process

  def terminate_process(self, process_id):
    # type: (str)
    """ Sends a terminate signal to the process with the specified
    *process_id*. If the process does not exist in the process manager, a
    #ValueError is raised. """

    with self._lock:
      try:
        process = self._processes[process_id]
      except KeyError:
        raise ValueError(process_id)
      process.terminate()

  def _run(self, poll_threshold, wait_on_stop):
    while True:
      # Stop the loop if that is requested. If we wait for processes to
      # complete, we only stop the loop if there are no more processes.
      stopped = self._stop_event.is_set()
      if stopped and not wait_on_stop:
        break

      with self._lock:

        if not self._heap:
          if stopped:  # We've waited for all processes to finish.
            break
          self._logger.debug('No processes queued, sleeping for default_poll_interval.')
          delta = self.default_poll_interval

        else:
          # Process the item that is next up in the queue.
          item = heapq.heappop(self._heap)
          delta = item.next_poll_time - self.time_provider()
          if delta <= poll_threshold:
            self._poll(item)
            continue
          else:
            self._requeue(item.process_id, item.poll_interval, delta)

      # Do not sleep longer than the default poll interval.
      delta = min(delta, self.default_poll_interval)
      time.sleep(delta)

    self._logger.info('Stopped.')

  def _poll(self, item):
    process = self._processes[item.process_id]
    code = process.poll()
    if code is None:
      self._requeue(item.process_id, item.poll_interval)
    else:
      del self._processes[item.process_id]
      try:
        self._logger.info('Process {!r} finished with exit code {!r}.'.format(
          item.process_id, code))
        self.event_sink.process_finished(item.process_id, process)
      except:
        self._logger.exception('Error {}.process_finished()'.format(
          type(self.event_sink).__name__))

  def _requeue(self, process_id, poll_interval, poll_next=None):
    next_poll_time = self.time_provider() + (poll_next or poll_interval)
    heap_item = self._HeapItem(next_poll_time, poll_interval, process_id)
    heapq.heappush(self._heap, heap_item)
