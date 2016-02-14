# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import json
import uuid

from . import app, config, utils, queue
from flask import request, render_template

API_GOGS = 'gogs'
API_GITHUB = 'github'


@app.route('/hook/push', methods=['POST'])
@utils.with_io_response(mimetype='text/plain')
@utils.with_logger()
def hook_push(logger):
  ''' PUSH event webhook. The URL parameter ``api`` must be specified
  for Flux to expect the correct JSON payload format. Supported values
  for ``api`` are

  * ``gogs``
  * ``github``

  If no or an invalid value is specified for this parameter, a 400
  Invalid Request response is generator. '''

  api = request.args.get('api')
  if api not in (API_GOGS, API_GITHUB):
    logger.error('invalid `api` URL parameter: {!r}'.format(api))
    return 400

  logger.info('PUSH event received. Processing JSON payload.')
  try:
    # XXX Determine encoding from Request Headers, if possible.
    data = json.loads(request.data.decode('utf8'))
  except (UnicodeDecodeError, ValueError) as exc:
    logger.error('Invalid JSON data received: {}'.format(exc))
    return 400

  if api == API_GOGS:
    owner = utils.get(data, 'repository.owner.username', str)
    name = utils.get(data, 'repository.name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'after', str)
  elif api == API_GITHUB:
    owner = utils.get(data, 'repository.owner.name', str)
    name = utils.get(data, 'repository.name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'after', str)
  else:
    assert False, "unreachable"

  if not name:
    logger.error('invalid JSON: no repository name received')
    return 400
  if not owner:
    logger.error('invalid JSON: no repository owner received')
    return 400
  if not ref:
    logger.error('invalid JSON: no Git ref received')
    return 400
  if not commit:
    logger.error('invalid JSON: no commit SHA received')
    return 400
  if len(commit) != 40:
    logger.error('invalid JSON: commit SHA has invalid length')
    return 400

  name = owner + '/' + name
  if name not in config.repos:
    logger.error('PUSH event rejected (unknown repository)')
    return 400

  repo = config.repos[name]
  if repo['secret'] != utils.get(data, 'secret'):
    logger.error('PUSH event rejected (invalid secret)')
    return 400

  if 'refs' in repo:
    if ref not in repo['refs']:
      logger.info('Git ref {!r} not whitelisted. No build dispatched'.format(ref))
      return 200
    else:
      logger.info('Git ref {!r} whitelisted. Continue build dispatch'.format(ref))

  try:
    builder = queue.Builder(repo, commit)
  except ValueError as exc:
    logger.error(str(exc))
    return 500

  queue.put(builder)
  logger.info('Dispatched to build queue.')
  logger.info('  build log: {!r}'.format(builder.build_log))
  logger.info('  build directory: {!r}'.format(builder.build_dir))
  return 200


@app.route('/')
@utils.requires_auth
def dashboard():
  context = {}
  context['page_title'] = 'Dashboard'
  context['queued_builds'] = queue.queue_snapshot()
  context['running_builds'] = queue.processing_snapshot()
  context['finished_builds'] = queue.finished_snapshot()
  print(context)
  return render_template('index.html', **context)
