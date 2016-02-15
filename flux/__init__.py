# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.
'''
Flux -- Lightweight private build server
========================================

Flux is a simple, Flask_ based build server that responds to Git
push events as triggered by GitHub, GitLab, BitBucket or Gogs.
While it is cross-platform and can on Windows, Linux and Mac OS,
it does not provide any kind of virtualization or container
management.

.. _Flask: http://flask.pocoo.org/
'''

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '1.0.0-dev'

import os, sys
import flask
app = flask.Flask(__name__)
app.template_folder = os.path.join(os.path.dirname(__file__), 'templates')
app.static_folder = os.path.join(os.path.dirname(__file__), 'static')

from . import config
app.jinja_env.globals['config'] = config
app.jinja_env.globals['flux'] = sys.modules[__name__]
app.secret_key = config.secret_key

from . import views, build, models

import subprocess


def main():
  ''' Runs the Flux Flask application and all required components. '''

  # Test if Git version is at least 2.3 (for GIT_SSH_COMMAND)
  git_version = subprocess.check_output(['git', '--version']).decode().strip()
  if git_version < 'git version 2.3':
    print('Error: {!r} installed but need at least 2.3'.format(git_version))
    sys.exit(1)

  # Make sure the root user exists and has all privileges.
  with models.Session() as session:
    models.User.create_root_if_not_exists(session)


  print(' * starting builder threads...')
  build.run_consumers(num_threads=config.parallel_builds)
  build.update_queue()
  try:
    ssl_context = config.ssl_context if config.ssl_enabled else None
    app.run(host=config.host, port=config.port, debug=config.debug, use_reloader=False, ssl_context=ssl_context)
  finally:
    print(' * stopping builder threads...')
    build.stop_consumers()
