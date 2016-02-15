# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
This module implements the Flux worker queue. Flux will start one or
more threads (based on the ``parallel_builds`` configuration value)
that will process the queue.
'''

import os, stat, shlex, shutil, subprocess
import time, traceback

from . import config, utils
from .models import Session, Build
from collections import deque
from threading import Event, Condition, Thread
from datetime import datetime


class BuildConsumer(object):
  ''' This class can start a number of threads that consume
  :class:`Build` objects and execute them. '''

  def __init__(self):
    self._cond = Condition()
    self._running = False
    self._queue = deque()
    self._terminate_events = {}
    self._threads = []

  def put(self, build):
    if not isinstance(build, Build):
      raise TypeError('expected Build instance')
    if build.status != Build.Status_Queued:
      raise TypeError('build status must be {!r}'.format(Build.Status_Queued))
    with self._cond:
      if build.id not in self._queue:
        self._queue.append(build.id)
        self._cond.notify()

  def terminate(self, build):
    ''' Given a :class:`Build` object, terminates the ongoing build
    process or removes the build from the queue and sets its status
    to "stopped". '''

    if not isinstance(build, Build):
      raise TypeError('expected Build instance')
    with self._cond:
      if build.id in self._terminate_events:
        self._terminate_events[build.id].set()
      elif build.id in self._queue:
        self._queue.remove(build.id)
        with Session() as session:
          build.status = build.Status_Stopped
          session.add(build)

  def stop(self, join=True):
    with self._cond:
      for event in self._terminate_events.values():
        event.set()
      self._running = False
      self._cond.notify()
    if join:
      [t.join() for t in self._threads]

  def start(self, num_threads=1):
    def worker():
      while True:
        with self._cond:
          while not self._queue and self._running:
            self._cond.wait()
          if not self._running:
            break
          build_id = self._queue.popleft()
        with Session() as session:
          build = session.query(Build).get(build_id)
          if not build or build.status != Build.Status_Queued:
            continue
        with self._cond:
          do_terminate = self._terminate_events[build_id] = Event()
        try:
          do_build(build, do_terminate)
        except BaseException as exc:
          traceback.print_exc()
        finally:
          with self._cond:
            self._terminate_events.pop(build_id)

    if num_threads < 1:
      raise ValueError('num_threads must be >= 1')
    with self._cond:
      if self._running:
        raise RuntimeError('already running')
      self._running = True
      self._threads = [Thread(target=worker) for i in range(num_threads)]
      [t.start() for t in self._threads]


_consumer = BuildConsumer()
enqueue = _consumer.put
terminate_build = _consumer.terminate
run_consumers = _consumer.start
stop_consumers = _consumer.stop


def update_queue(consumer=None):
  ''' Make sure all builds in the database that are still queued
  are actually queued in the BuildConsumer. '''

  if consumer is None:
    consumer = _consumer
  with Session() as session:
    for build in session.query(Build).filter_by(status=Build.Status_Queued):
      enqueue(build)


def do_build(build, terminate_event):
  print(' * build {}#{} started'.format(build.repo.name, build.num))
  assert build.status == Build.Status_Queued

  with Session() as session:
    # Mark the build as started.
    build.status = Build.Status_Building
    build.date_started = datetime.now()
    session.add(build)

  logfile = None
  logger = None

  try:
    build_path = build.path()
    utils.makedirs(os.path.dirname(build_path))
    logfile = open(build.path(build.Data_Log), 'w')
    logger = utils.create_logger(logfile)

    try:
      if do_build_(build, build_path, logger, logfile, terminate_event):
        build.status = Build.Status_Success
      else:
        if terminate_event.is_set():
          build.status = Build.Status_Stopped
        else:
          build.status = Build.Status_Error
    finally:
      # Create a ZIP from the build directory.
      if os.path.isdir(build_path):
        logger.info('[Flux]: Zipping build directory...')
        utils.zipdir(build_path, build_path + '.zip')
        shutil.rmtree(build_path)
        logger.info('[Flux]: Done')
  except BaseException as exc:
    build.status = Build.Status_Error
    if logger:
      logger.exception(exc)
    else:
      traceback.print_exc()
  finally:
    if logfile:
      logfile.close()
    build.date_finished = datetime.now()
    with Session() as session:
      session.add(build)

  return build.status == Build.Status_Success


def do_build_(build, build_path, logger, logfile, terminate_event):
  logger.info('[Flux]: build {}#{} started'.format(build.repo.name, build.num))

  # Clone the repository.
  ssh_command = utils.ssh_command(None, identity_file=config.ssh_identity_file)  # Enables batch mode
  env = {'GIT_SSH_COMMAND': ' '.join(map(shlex.quote, ssh_command))}
  logger.info('[Flux]: GIT_SSH_COMMAND={!r}'.format(env['GIT_SSH_COMMAND']))
  clone_cmd = ['git', 'clone', build.repo.clone_url, build_path, '--recursive']
  res = utils.run(clone_cmd, logger, env=env)
  if res != 0:
    logger.error('[Flux]: unable to clone repository')
    return False

  if terminate_event.is_set():
    logger.info('[Flux]: build stopped')
    return False

  # Checkout the correct commit.
  checkout_cmd = ['git', 'checkout', build.commit_sha]
  res = utils.run(checkout_cmd, logger, cwd=build_path)
  if res != 0:
    logger.error('[Flux]: failed to checkout {!r}'.format(build.commit_sha))
    return False

  if terminate_event.is_set():
    logger.info('[Flux]: build stopped')
    return False

  # Delete the .git folder to save space. We don't need it anymore.
  shutil.rmtree(os.path.join(build_path, '.git'))

  # Find the build script that we need to execute.
  script_fn = None
  for fname in config.buildscripts:
    script_fn = os.path.join(build_path, fname)
    if os.path.isfile(script_fn):
      break
    script_fn = None

  if not script_fn:
    choices = '{' + ','.join(map(str, config.buildscripts)) + '}'
    logger.error('[Flux]: no build script found, choices are ' + choices)
    return False

  # Make sure the build script is executable.
  st = os.stat(script_fn)
  os.chmod(script_fn, st.st_mode | stat.S_IEXEC)

  # Execute the script.
  logger.info('[Flux]: executing {}'.format(os.path.basename(script_fn)))
  logger.info('$ ' + shlex.quote(script_fn))
  popen = subprocess.Popen(script_fn, cwd=build_path,
    stdout=logfile, stderr=subprocess.STDOUT, stdin=None)

  # Wait until the process finished or the terminate event is set.
  while popen.poll() is None and not terminate_event.is_set():
    time.sleep(0.5)
  if terminate_event.is_set():
    try:
      popen.terminate()
    except OSError as exc:
      logger.exception(exc)
    logger.error('[Flux]: build stopped. build script terminated')
    return False

  logger.info('[Flux]: exit-code {}'.format(popen.returncode))
  return popen.returncode == 0
