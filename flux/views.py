# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import json
import uuid

from . import app, config, utils, queue
from flask import request

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
  elif api == API_GITHUB:
    owner = utils.get(data, 'repository.owner.name', str)
    name = utils.get(data, 'repository.name', str)
  else:
    assert False, "unreachable"

  if not name or not owner:
    logger.error('"repository.name" or "repository.owner.username" not received or invalid.')
    return 400

  name = owner + '/' + name
  if name not in config.repos:
    logger.error('PUSH event rejected (unknown repository)')
    return 400

  repo = config.repos[name]
  if repo['secret'] != utils.get(data, 'secret'):
    logger.error('PUSH event rejected (invalid secret)')
    return 400

  commit = utils.get(data, 'after', str)
  if not commit or len(commit) != 40:
    logger.error('Invalid commit SHA received: {!r}'.format(commit))
    return 400

  try:
    builder = queue.Builder(repo, commit)
  except ValueError as exc:
    logger.error(str(exc))
    return 500

  queue.put(builder)
  logger.info('Dispatched to build queue.')
  logger.info('Build directory is {!r}'.format(builder.build_dir))
  logger.info('Build log is {!r}'.format(builder.build_dir))
  return 200
