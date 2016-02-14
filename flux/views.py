# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import json
import uuid

from . import app, config, utils
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
    return

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
    return

  name = owner + '/' + name
  if name not in config.repos:
    logger.error('PUSH event rejected (unknown repository)')
    return

  repo = config.repos[name]
  if repo['secret'] != utils.get(data, 'secret'):
    logger.error('PUSH event rejected (invalid secret)')
    return


  ssh_url = repo['clone_url'].rpartition(':')[0]
  ssh_identity_file = repo.get('ssh_identity_file', config.ssh_identity_file)
  ssh_command = utils.ssh_command(
    ssh_url, 'exit', test=True, identity_file=ssh_identity_file,
    options={'BatchMode': 'yes'})

  # Check if we have access to the Git server. Note that cloning
  # could still fail if the Git server denies the access, but we
  # can't test it here.
  access = utils.run(ssh_command, logger)
  if access != 0:
    logger.error('Flux can not access this Git server')
    return

  worker_id = uuid.uuid4()
  logger.info('Dispatching worker into build queue. ID: {}'.format(worker_id))
  logger.warning('NOTE: The above notice is a scam. I actually didn\'t dispatch a worker. Haha. Funny')
