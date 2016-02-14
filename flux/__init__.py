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

from . import views, queue, models


def main():
  ''' Runs the Flux Flask application and all required components. '''

  # Make sure the root user exists and has all privileges.
  session = models.Session()
  root = session.query(models.User).filter(
    models.User.name == config.root_user).one_or_none()
  if not root:
    root = models.User(
      name=config.root_user, passhash=utils.hash_pw(config.root_password),
      can_manage=True, can_download_artifacts=True, can_view_buildlogs=True)
    session.add(root)
  else:
    root.can_manage = True
    root.can_download_artifacts = True
    root.can_view_buildlogs = True
    session.add(root)
  session.commit()

  # XXX Test if Git version is at least 2.3 (for GIT_SSH_COMMAND)
  queue.start()
  try:
    app.run(host=config.host, port=config.port, debug=config.debug)
  finally:
    queue.stop()
