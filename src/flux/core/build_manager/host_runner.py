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

""" A script that is spawned to execute a build on the host. Expects the
#BuildData JSON payload via stdin. """

from flux.core.build_manager import BuildData
from flux.clients.remote import RemoteBuildClient
from flux.models import Build
from flux.utils import ssh_command
from shlex import quote

import argparse
import json
import logging
import os
import nr.fs
import shutil
import subprocess
import sys

logging.basicConfig(
  format='[%(name)s - %(levelname)s - %(asctime)s]: %(message)s',
  level=logging.INFO)
logger = logging.getLogger('flux.core.build_manager.host_runner')


def clone_repository(build_path, identity_file, build_data):
  nr.fs.makedirs(build_path)
  env = os.environ.copy()
  command = ssh_command(identity_file=identity_file)
  env['GIT_SSH_COMMAND'] = ' '.join(map(quote, command))
  command = ['git', 'clone', build_data.repository_clone_url, build_path,
             '--recursive']
  subprocess.check_call(command, env=env)


def checkout_repository(build_path, build_data, build_client):
  # Builds that have been initiated on a specific ref have an all-zero SHA.
  if build_data.build_commit_sha == "0" * 32:
    build_rev = build_data.build_ref
    update_sha = True
  else:
    build_rev = build_data.build_commit_sha
    update_sha = False

  logger.info('Checking out "{}"'.format(build_rev))
  command = ['git', 'checkout', '-q', build_rev]
  subprocess.check_call(command, cwd=build_path)

  # Report back the Commit SHA and full ref. This is important when the
  # build was initiated manually to consistent rev data in the build history.
  command = ['git', 'rev-parse', 'HEAD']
  build_data.build_commit_sha = subprocess.check_output(command, cwd=build_path).decode().strip()
  command = ['git', 'rev-parse', '--symbolic-full-name', build_rev]
  build_data.build_ref = subprocess.check_output(command, cwd=build_path).decode().strip()

  logger.info('Reporting back rev and SHA (rev: {}, sha: {})'.format(
    build_data.build_ref, build_data.build_commit_sha))
  build_client.set_revision_info(build_data.build_id,
    build_data.build_ref, build_data.build_commit_sha)


def apply_overrides(build_path, filenames, build_data, build_client):
  for filename in filenames:
    logger.info('Applying "{}"'.format(filename))
    dest = os.path.join(build_path, filename)
    nr.fs.makedirs(os.path.dirname(dest))
    with build_client.get_override(build_data.build_id, filename) as src:
      with open(dest, 'wb') as dst:
        shutil.copyfileobj(src, dst)


def find_build_script(build_path, filenames):
  for filename in filenames:
    filename = os.path.join(build_path, filename)
    if os.path.isfile(filename):
      return filename
  raise EnvironmentError('no build script found (choices are {!r})'.format(
    filenames))


def run_build_script(build_path, build_script):
  nr.fs.chmod(build_script, 'u+x')
  popen = subprocess.Popen([build_script], cwd=build_path, stdin=None)
  try:
    popen.wait()
  except Exception:
    logger.exception('Error waiting for process.')
    try:
      popen.terminate()
    except Exception:
      logger.exception('Error terminating process.')
  return popen.returncode


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('build_path')
  parser.add_argument('build_scripts', nargs='+')
  args = parser.parse_args()

  logger.info('Loading BuildData JSON payload from stdin.')
  build_data = BuildData.from_json(json.loads(sys.stdin.readline()))
  build_client = RemoteBuildClient.from_build_data(build_data)

  logger.info('Setting build status to {}.'.format(Build.Status_Building))
  build_client.set_status(build_data.build_id, Build.Status_Building)

  build_client.start_section(build_data.build_id, 'Clone repository')
  clone_repository(args.build_path, build_data.identity_file, build_data)
  checkout_repository(args.build_path, build_data, build_client)

  # TODO (@NiklasRosenstein): Implement GitFolderHandling

  override_filenames = build_client.list_overrides(build_data.build_id)
  if override_filenames:
    build_client.start_section(build_data.build_id, 'Apply overrides')
    apply_overrides(args.build_path, override_filenames, build_data, build_client)

  build_client.start_section(build_data.build_id, 'Run build script')
  build_script = find_build_script(args.build_path, args.build_scripts)
  returncode = run_build_script(args.build_path, build_script)

  # TODO (@NiklasRosenstein): Implement GitFolderHandling

  return returncode


if __name__ == '__main__':
  sys.exit(main())
