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

from . import app
from six.moves.urllib.parse import urlparse
import argparse
import contextlib
import os
import re
import subprocess
import sys


def get_argument_parser(prog):
  parser = argparse.ArgumentParser(prog=prog)
  parser.add_argument('-c','--config-file', help='Flux CI config file to load')
  return parser


def main(argv=None, prog=None):
  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)

  # Add possible locations of flux config.
  sys.path.insert(0, '.')
  if args.config_file and os.path.isfile(args.config_file):
    sys.path.insert(0, os.path.dirname(args.config_file))

  # Load config as global.
  from flux import config
  config.load(args.config_file)

  check_requirements()
  app = init_application_state()
  run_web(app)


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


def init_application_state():
  import flux
  from flux import config, models

  # Initialize app globals.
  app.jinja_env.globals['config'] = config
  app.jinja_env.globals['flux'] = flux
  app.secret_key = config.secret_key
  app.config['DEBUG'] = config.debug
  app.config['SERVER_NAME'] = config.server_name

  # Initialize some stuff defined in the config.
  for dirname in [config.root_dir, config.build_dir, config.override_dir, config.customs_dir]:
    if not os.path.exists(dirname):
        os.makedirs(dirname)

  # Initialize the database.
  models.db.bind(**config.database)
  models.db.generate_mapping(create_tables=True)

  # Ensure that the root user exists.
  with models.session():
    models.User.create_or_update_root()

  # Create a dispatcher for the sub-url under which the app is run.
  url_prefix = urlparse(config.app_url).path
  if url_prefix and url_prefix != '/':
    from werkzeug.wsgi import DispatcherMiddleware
    return DispatcherMiddleware(flask.Flask('_dummy_app'), {
      url_prefix: app,
    })
  else:
    return app


@contextlib.contextmanager
def wrap_init_shutdown(obj, *args, **kwargs):
  obj.init(*args, **kwargs)
  try:
    yield
  finally:
    obj.shutdown()


def run_web(app):
  import logging
  logging.basicConfig(format='[%(name)s %(levelname)s %(asctime)s]: %(message)s',
    level=logging.INFO)
  from flux import config
  with wrap_init_shutdown(config.build_manager), \
       wrap_init_shutdown(config.scheduler, config.build_manager):
    app.logger.info('Starting Flask application.')
    from werkzeug.serving import run_simple
    run_simple(config.host, config.port, app, use_debugger=config.debug,
      use_reloader=config.debug)


if __name__ == '__main__':
  main()
