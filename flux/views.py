# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import json
import uuid

from . import app, config, utils
from .models import Session, User, Repository, Build, get_target_for, get_public_key
from flask import request, redirect, url_for, render_template, abort
from datetime import datetime

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

  session = Session()
  repo = session.query(Repository).filter_by(name=name).one_or_none()
  if not repo:
    logger.error('PUSH event rejected (unknown repository)')
    return 400
  if repo.secret != utils.get(data, 'secret'):
    logger.error('PUSH event rejected (invalid secret)')
    return 400

  # XXX Support whitelisting repositories
  #if 'refs' in repo:
  #  if ref not in repo['refs']:
  #    logger.info('Git ref {!r} not whitelisted. No build dispatched'.format(ref))
  #    return 200
  #  else:
  #    logger.info('Git ref {!r} whitelisted. Continue build dispatch'.format(ref))

  build = Build(repo=repo, commit_sha=commit, num=repo.build_count, ref=ref,
    status=Build.Status_Queued, date_queued=datetime.now(), date_started=None,
    date_finished=None)
  repo.build_count += 1
  session.add(repo)
  session.add(build)
  session.commit()

  logger.info('Build #{} for repository {} queued'.format(build.num, repo.name))
  logger.info(config.app_url + build.url())
  return 200


@app.route('/')
@utils.requires_auth
def dashboard():
  session = Session()
  context = {}
  context['repositories'] = session.query(Repository).order_by(Repository.name).all()
  context['user'] = request.user
  context['public_key'] = get_public_key()
  return render_template('dashboard.html', **context)


@app.route('/repo/<path:path>')
@utils.requires_auth
def view_repo(path):
  session = Session()
  repo = get_target_for(session, path)
  if not isinstance(repo, Repository):
    return abort(404)
  return render_template('view_repo.html', user=request.user, repo=repo)


@app.route('/build/<path:path>')
@utils.requires_auth
def view_build(path):
  session = Session()
  build = get_target_for(session, path)
  if not isinstance(build, Build):
    return abort(404)
  return render_template('view_build.html', user=request.user, build=build)


@app.route('/new/repo', methods=['GET', 'POST'])
@utils.requires_auth
def new_repo():
  if not request.user.can_manage:
    return abort(403)
  errors = []
  if request.method == 'POST':
    secret = request.form.get('repo_secret', '')
    clone_url = request.form.get('repo_clone_url', '')
    repo_name = request.form.get('repo_name', '').strip()
    if len(repo_name) < 3 or repo_name.count('/') != 1:
      errors.append('Invalid repository name. Format must be owner/repo')
    if not clone_url:
      errors.append('No clone URL specified')
    if not errors:
      session = Session()
      repo = session.query(Repository).filter_by(name=repo_name).one_or_none()
      if repo:
        errors.append('Repository {!r} already exists'.format(repo_name))
      else:
        repo = Repository(name=repo_name, clone_url=clone_url, secret=secret, build_count=0)
        session.add(repo)
        session.commit()
        return redirect(url_for('dashboard'))
  return render_template('new_repo.html', user=request.user, errors=errors)


@app.route('/download')
@utils.requires_auth
def download():
  repo = request.args.get('repo', '')
  build = request.args.get('build', '')
  mode = request.args.get('data', '')
  if mode not in (Build.Data_Artifact, Build.Data_Log):
    return abort(404)

  session = Session()
  build = get_target_for(session, repo + '/' + build)
  if not isinstance(build, Build) or not build.exists(mode):
    return abort(404)
  if not request.user.can_download_artifacts:
    return abort(403)

  mime = 'application/zip' if mode == Build.Data_Artifact else 'text/plain'
  return utils.stream_file(build.path(mode), mime=mime)



@app.route('/delete')
@utils.requires_auth
def delete():
  if not request.user.can_manage:
    return abort(403)
  path = request.args.get('repo', '')
  build = request.args.get('build', '')
  if build:
    path += '/' + build
  session = Session()
  obj = get_target_for(session, path)
  if not obj:
    return abort(404)
  try:
    session.delete(obj)
    session.commit()
  except Build.CanNotDelete as exc:
    utils.flash(str(exc))
    referer = request.headers.get('Referer', url_for('dashboard'))
    return redirect(referer)
  return redirect(url_for('dashboard'))
