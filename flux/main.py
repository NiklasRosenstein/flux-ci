# -*- coding: utf8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2018  Niklas Rosenstein
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

import argparse
import re
import subprocess
import sys


def get_argument_parser(prog=None):
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('--web', action='store_true')
  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  if not args.web:
    parser.print_usage()
    return 0

  import sys

  # The flux_config module could be found here.
  sys.path.insert(0, '.')
  from flux import config

  start_web()


def check_requirements():
  """
  Checks some system requirements. If they are not met, prints an error and
  exits the process. Currently, this only checks if the required Git version
  is met (>= 2.3).
  """

  # Test if Git version is at least 2.3 (for GIT_SSH_COMMAND)
  git_version = subprocess.check_output(['git', '--version']).decode().strip()
  git_version = re.search('^git version (\d\.\d+)', git_version)
  if git_version:
    git_version = git_version.group(1)
  if not git_version or int(git_version.split('.')[1]) < 3:
    print('Error: {!r} installed but need at least 2.3'.format(git_version))
    sys.exit(1)


def start_web():
  check_requirements()

  import flux
  from flux import app, config, utils
  app.jinja_env.globals['config'] = config
  app.jinja_env.globals['flux'] = flux
  app.secret_key = config.secret_key
  app.config['DEBUG'] = config.debug
  app.config['SERVER_NAME'] = config.server_name
  print('DEBUG = {}'.format(config.debug))
  print('SERVER_NAME = {}'.format(config.server_name))

  from flux import views, build, models
  from urllib.parse import urlparse

  # Make sure the root user exists and has all privileges, and that
  # the password is up to date.
  with models.Session() as session:
    models.User.create_or_update_root(session)

  # Create a dispatcher for the sub-url under which the app is run.
  url_prefix = urlparse(config.app_url).path
  if url_prefix and url_prefix != '/':
    print(url_prefix)
    from werkzeug.wsgi import DispatcherMiddleware
    target_app = DispatcherMiddleware(flask.Flask('_dummy_app'), {
      url_prefix: app,
    })
  else:
    target_app = app

  app.logger.info('Starting builder threads...')
  build.run_consumers(num_threads=config.parallel_builds)
  build.update_queue()
  try:
    from werkzeug.serving import run_simple
    run_simple(config.host, config.port, target_app, use_reloader=False)
  finally:
    app.logger.info('Stopping builder threads...')
    build.stop_consumers()


_entry_point = lambda: sys.exit(main())


if __name__ == '__main__':
  _entry_point()
