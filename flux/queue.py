# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
This module implements the Flux worker queue. Flux will start one or
more threads (based on the ``parallel_builds`` configuration value)
that will process the queue.
'''

import collections
import datetime
import os
import queue
import shlex
import shutil
import stat
import sys
import threading
import traceback
import uuid
from . import config, utils


class Builder(object):
  ''' This class represents a builder for a repository and a specific
  revision that will be queued in the Flux build queue.

  :raise ValueError: If the *build_dir* or *build_log* already exists.

  .. attribute:: repo

    The repository configuration dictionary.

  .. attribute:: commit_sha

    The commit SHA number to checkout for the repository.

  .. attribute:: build_dir

    The build directory in which the repository will be cloned to
    and in which the build will be executed in. If not explicitly
    specified in the constructor, it will automatically be determined
    from the *repo* configuration or the global Flux configuration
    plus the *commit_sha*.

  .. attribute:: build_log

    The filename in which the full build log output will be piped
    into. If not explicitly specified in the constructor, this will
    be the path of the *build_dir* plus the ``.log`` suffix.

  .. attribute:: created

    A :class:`datetime.datetime` instance of the time the Builder
    instance has been created.

  .. attribute:: logfile

    An open file-object to the :attr:`build_log` file.
  '''

  def __init__(self, repo, commit_sha, build_dir=None, build_log=None):
    if not build_dir:
      build_dir = repo.get('build_dir', config.build_dir)
      build_dir = os.path.join(build_dir, commit_sha)
    if not build_log:
      build_log = build_dir + '.log'
    self.repo = repo
    self.commit_sha = commit_sha
    self.build_dir = build_dir
    self.build_log = build_log
    self.created = datetime.datetime.now()
    self.logfile = None

    if os.path.exists(build_dir):
      raise ValueError('Build directory {!r} already exists'.format(build_dir))
    if os.path.exists(build_log):
      raise ValueError('Build log {!r} already exists'.format(build_log))
    os.makedirs(build_dir)
    self.logfile = open(self.build_log, 'w')

    self.logger = utils.create_logger(self.logfile)

  def __del__(self):
    logfile = getattr(self, 'logfile', None)
    if logfile:
      logfile.close()
      self.logfile = None

  def execute_build(self):
    self.logger.info('[Flux]: Starting build on {}'.format(datetime.datetime.now()))
    self.logger.info('[Flux]: Queued since {}'.format(self.created))

    # Compute thr GIT_SSH_COMMAND.
    ssh_ifile = self.repo.get('ssh_identity_file', config.ssh_identity_file)
    ssh_cmd = utils.ssh_command(None, identity_file=ssh_ifile)
    env = {'GIT_SSH_COMMAND': ' '.join(map(shlex.quote, ssh_cmd))}
    self.logger.info('GIT_SSH_COMMAND={}'.format(env['GIT_SSH_COMMAND']))

    # Clone the repository.
    clone_cmd = ['git', 'clone', self.repo['clone_url'], self.build_dir, '--recursive']
    if utils.run(clone_cmd, self.logger, env=env) != 0:
      self.logger.info('[Flux]: Could not clone repository.')
      return False

    # Checkout the correct commit.
    checkout_cmd = ['git', 'checkout', self.commit_sha]
    if utils.run(checkout_cmd, self.logger, cwd=self.build_dir) != 0:
      self.logger.info('[Flux]: Failed to checkout {!r}'.format(self.commit_sha))
      return False

    # Delete the .git folder to save space. We don't need it anymore.
    shutil.rmtree(os.path.join(self.build_dir, '.git'))

    # Find the build script that we need to execute.
    script_fn = None
    for fname in config.buildscripts:
      script_fn = os.path.join(self.build_dir, fname)
      if os.path.isfile(script_fn):
        break
      script_fn = None

    if not script_fn:
      choices = '{' + ','.join(map(str, config.buildscripts)) + '}'
      self.logger.info('[Flux]: No build script found. Available choices are ' + choices)
      return False

    # Make sure the build script is executable.
    st = os.stat(script_fn)
    os.chmod(script_fn, st.st_mode | stat.S_IEXEC)

    # Execute the script.
    code = utils.run([script_fn], self.logger, shell=True)
    self.logger.info('[Flux]: Build script returned with exit-code {}'.format(code))
    return code == 0

  def on_exception(self, exc):
    self.logger.exception(exc)


class BuilderQueue(object):
  ''' This class represents a queue of :class:`Builder` objects that
  is processed by a number of threads. The thread number can be
  specified on :meth:`start` and defaults to the ``parallel_builds``
  config value. '''

  def __init__(self):
    self._queue = collections.deque()
    self._cond = threading.Condition()
    self._running = False
    self._threads = []

  def put(self, builder):
    ''' Add a :class:`Builder` to the queue. '''

    if not isinstance(builder, Builder):
      raise TypeError('expected Builder instance')

    with self._cond:
      if builder in self._queue:
        raise ValueError('builder already in queue')
      self._queue.append(builder)
      self._cond.notify()

  def start(self, num_threads=None):
    ''' Start the queue and the processing threads. *num_threads*
    specifies the number of threads (and thus the number of builders
    that are executed in parallel). The default value is the
    ``parallel_builds`` configuration value. '''

    with self._cond:
      if self._running:
        raise RuntimeError('queue already running')

    if num_threads is None:
      num_threads = config.parallel_builds

    def worker():
      while True:
        with self._cond:
          while not self._queue and self._running:
            self._cond.wait()
          if not self._running:
            break
          builder = self._queue.popleft()
          try:
            builder.execute_build()
          except BaseException as exc:
            builder.on_exception(exc)

    self._running = True
    self._threads = [threading.Thread(target=worker) for i in range(num_threads)]
    [t.start() for t in self._threads]

  def stop(self):
    with self._cond:
      self._running = False
      self._cond.notify()
    [t.join() for t in self._threads]
    self._threads = []


queue = BuilderQueue()


def put(*args, **kwargs):
  return queue.put(*args, **kwargs)


def start(*args, **kwargs):
  return queue.start(*args, **kwargs)


def stop(*args, **kwargs):
  return queue.stop(*args, **kwargs)
