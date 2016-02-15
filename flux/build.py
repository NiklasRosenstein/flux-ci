# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
This module implements the Flux worker queue. Flux will start one or
more threads (based on the ``parallel_builds`` configuration value)
that will process the queue.
'''

import os, stat, shlex, shutil, subprocess
import time, threading
import traceback

from . import config, utils
from .models import Session, Build
from datetime import datetime


class BuilderThread(threading.Thread):

  def __init__(self):
    super().__init__()
    self.running = False
    self.lock = threading.Lock()

  def stop(self, join=True):
    with self.lock:
      self.running = False
    self.join()

  def start(self):
    with self.lock:
      if self.running:
        raise RuntimeError('already running')
      self.running = True
    return super().start()

  def run(self):
    while True:
      with self.lock:
        if not self.running:
          break
      session = Session()
      build = session.query(Build).filter_by(status=Build.Status_Queued).first()
      if build:
        try:
          do_build(session, build)
        except BaseException:
          traceback.print_exc()
      else:
        # Sleep five seconds before checking the next check.
        time.sleep(5)


_thread = BuilderThread()
start_threads = _thread.start
stop_threads = _thread.stop


def do_build(session, build):
  print(' * build {}#{} started'.format(build.repo.name, build.num))
  assert build.status == Build.Status_Queued

  # Mark the build as started.
  build.status = Build.Status_Building
  build.date_started = datetime.now()
  session.add(build)
  session.commit()

  logfile = None
  logger = None

  try:
    build_path = build.path()
    print(build_path)
    utils.makedirs(os.path.dirname(build_path))
    logfile = open(build.path(build.Data_Log), 'w')
    logger = utils.create_logger(logfile)

    try:
      if do_build_(build, build_path, logger, logfile):
        build.status = Build.Status_Success
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
    session.add(build)
    session.commit()

  return build.status == Build.Status_Success


def do_build_(build, build_path, logger, logfile):
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

  # Checkout the correct commit.
  checkout_cmd = ['git', 'checkout', build.commit_sha]
  res = utils.run(checkout_cmd, logger, cwd=build_path)
  if res != 0:
    logger.error('[Flux]: failed to checkout {!r}'.format(build.commit_sha))
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
  popen.wait()
  logger.info('[Flux]: exit-code {}'.format(popen.returncode))
  return popen.returncode == 0
