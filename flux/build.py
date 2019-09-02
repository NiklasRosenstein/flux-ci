# Copyright (c) 2016  Niklas Rosenstein
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
'''
This module implements the Flux worker queue. Flux will start one or
more threads (based on the ``parallel_builds`` configuration value)
that will process the queue.
'''

from flux import app, config, utils, models
from flux.enums import GitFolderHandling
from flux.models import select, Build
from collections import deque
from threading import Event, Condition, Thread
from datetime import datetime
from distutils import dir_util

import contextlib
import os
import shlex
import shutil
import stat
import subprocess
import time
import traceback


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
    assert build.id is not None
    # TODO: Check if the build is commited to the database, we should'nt
    #       enqueue it before it is.
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
      build.status = build.Status_Stopped

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
        with models.session():
          build = Build.get(id=build_id)
          if not build or build.status != Build.Status_Queued:
            continue
        with self._cond:
          do_terminate = self._terminate_events[build_id] = Event()
        try:
          do_build(build_id, do_terminate)
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

  def is_running(self, build):
    with self._cond:
      return build.id in self._queue


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
  with models.session():
    for build in select(x for x in Build if x.status == Build.Status_Queued):
      enqueue(build)
    for build in select(x for x in Build if x.status == Build.Status_Building):
      if not consumer.is_running(build):
        build.status = Build.Status_Stopped

def deleteGitFolder(build_path):
  shutil.rmtree(os.path.join(build_path, '.git'))

def do_build(build_id, terminate_event):
  """
  Performs the build step for the build in the database with the specified
  *build_id*.
  """

  logfile = None
  logger = None
  status = None

  with contextlib.ExitStack() as stack:
    try:
      try:
        # Retrieve the current build information.
        with models.session():
          build = Build.get(id=build_id)
          app.logger.info('Build {}#{} started.'.format(build.repo.name, build.num))

          build.status = Build.Status_Building
          build.date_started = datetime.now()

          build_path = build.path()
          override_path = build.path(Build.Data_OverrideDir)
          utils.makedirs(os.path.dirname(build_path))
          logfile = stack.enter_context(open(build.path(build.Data_Log), 'w'))
          logger = utils.create_logger(logfile)

          # Prefetch the repository member as it is required in do_build_().
          build.repo

        # Execute the actual build process (must not perform writes to the
        # 'build' object as the DB session is over).
        if do_build_(build, build_path, override_path, logger, logfile, terminate_event):
          status = Build.Status_Success
        else:
          if terminate_event.is_set():
            status = Build.Status_Stopped
          else:
            status = Build.Status_Error

      finally:
        # Create a ZIP from the build directory.
        if os.path.isdir(build_path):
          logger.info('[Flux]: Zipping build directory...')
          utils.zipdir(build_path, build_path + '.zip')
          utils.rmtree(build_path, remove_write_protection=True)
          logger.info('[Flux]: Done')

    except BaseException as exc:
      with models.session():
        build = Build.get(id=build_id)
        build.status = Build.Status_Error
        if logger:
          logger.exception(exc)
        else:
          app.logger.exception(exc)

    finally:
      with models.session():
        build = Build.get(id=build_id)
        if status is not None:
          build.status = status
        build.date_finished = datetime.now()

  return status == Build.Status_Success


def do_build_(build, build_path, override_path, logger, logfile, terminate_event):
  logger.info('[Flux]: build {}#{} started'.format(build.repo.name, build.num))

  # Clone the repository.
  if build.repo and os.path.isfile(utils.get_repo_private_key_path(build.repo)):
    identity_file = utils.get_repo_private_key_path(build.repo)
  else:
    identity_file = config.ssh_identity_file

  ssh_command = utils.ssh_command(None, identity_file=identity_file)  # Enables batch mode
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

  if build.ref and build.commit_sha == ("0" * 32):
    build_start_point = build.ref
    is_ref_build = True
  else:
    build_start_point = build.commit_sha
    is_ref_build = False

  # Checkout the correct build_start_point.
  checkout_cmd = ['git', 'checkout', build_start_point]
  res = utils.run(checkout_cmd, logger, cwd=build_path)
  if res != 0:
    logger.error('[Flux]: failed to checkout {!r}'.format(build_start_point))
    return False

  # If checkout was initiated by Start build, update commit_sha and ref of build
  if is_ref_build:
    # update commit sha
    get_ref_sha_cmd = ['git', 'rev-parse', 'HEAD']
    res_ref_sha, res_ref_sha_stdout = utils.run(get_ref_sha_cmd, logger, cwd=build_path, return_stdout=True)
    if res_ref_sha == 0 and res_ref_sha_stdout != None:
      with models.session():
        Build.get(id=build.id).commit_sha = res_ref_sha_stdout.strip()
    else:
      logger.error('[Flux]: failed to read current sha')
      return False
    # update ref; user could enter just branch name, e.g 'master'
    get_ref_cmd = ['git', 'rev-parse', '--symbolic-full-name', build_start_point]
    res_ref, res_ref_stdout = utils.run(get_ref_cmd, logger, cwd=build_path, return_stdout=True)
    if res_ref == 0 and res_ref_stdout != None and res_ref_stdout.strip() != 'HEAD' and res_ref_stdout.strip() != '':
      with models.session():
        Build.get(id=build.id).ref = res_ref_stdout.strip()
    elif res_ref_stdout.strip() == '':
      # keep going, used ref was probably commit sha
      pass
    else:
      logger.error('[Flux]: failed to read current ref')
      return False

  if terminate_event.is_set():
    logger.info('[Flux]: build stopped')
    return False

  # Deletes .git folder before build, if is configured so.
  if config.git_folder_handling == GitFolderHandling.DELETE_BEFORE_BUILD or config.git_folder_handling == None:
    logger.info('[Flux]: removing .git folder before build')
    deleteGitFolder(build_path)

  # Copy over overridden files if any
  if os.path.exists(override_path):
    dir_util.copy_tree(override_path, build_path);

  # Find the build script that we need to execute.
  script_fn = None
  for fname in config.build_scripts:
    script_fn = os.path.join(build_path, fname)
    if os.path.isfile(script_fn):
      break
    script_fn = None

  if not script_fn:
    choices = '{' + ','.join(map(str, config.build_scripts)) + '}'
    logger.error('[Flux]: no build script found, choices are ' + choices)
    return False

  # Make sure the build script is executable.
  st = os.stat(script_fn)
  os.chmod(script_fn, st.st_mode | stat.S_IEXEC)

  # Execute the script.
  logger.info('[Flux]: executing {}'.format(os.path.basename(script_fn)))
  logger.info('$ ' + shlex.quote(script_fn))
  popen = subprocess.Popen([script_fn], cwd=build_path,
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

  # Deletes .git folder after build, if is configured so.
  if config.git_folder_handling == GitFolderHandling.DELETE_AFTER_BUILD:
    logger.info('[Flux]: removing .git folder after build')
    deleteGitFolder(build_path)

  logger.info('[Flux]: exit-code {}'.format(popen.returncode))
  return popen.returncode == 0
