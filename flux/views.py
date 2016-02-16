# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import json
import uuid

from . import app, config, utils
from .build import enqueue, terminate_build
from .models import Session, User, Repository, Build, get_target_for, get_public_key
from flask import request, session, redirect, url_for, render_template, abort
from datetime import datetime

API_GOGS = 'gogs'
API_GITHUB = 'github'


@app.route('/hook/push', methods=['POST'])
@utils.with_io_response(mimetype='text/plain')
@utils.with_logger()
@utils.with_dbsession
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

  session = request.db_session
  repo = session.query(Repository).filter_by(name=name).one_or_none()
  if not repo:
    logger.error('PUSH event rejected (unknown repository)')
    return 400
  if repo.secret != utils.get(data, 'secret'):
    logger.error('PUSH event rejected (invalid secret)')
    return 400
  if not repo.check_accept_ref(ref):
    logger.info('Git ref {!r} not whitelisted. No build dispatched'.format(ref))
    return 200

  build = Build(repo=repo, commit_sha=commit, num=repo.build_count, ref=ref,
    status=Build.Status_Queued, date_queued=datetime.now(), date_started=None,
    date_finished=None)
  repo.build_count += 1
  session.add(repo)
  session.add(build)
  session.commit()

  enqueue(build)
  logger.info('Build #{} for repository {} queued'.format(build.num, repo.name))
  logger.info(config.app_url + build.url())
  return 200


@app.route('/')
@utils.requires_auth
@utils.with_dbsession
def dashboard():
  session = request.db_session
  context = {}
  context['repositories'] = session.query(Repository).order_by(Repository.name).all()
  context['user'] = request.user
  context['public_key'] = get_public_key()
  context['all_users'] = session.query(User).all()
  return render_template('dashboard.html', **context)


@app.route('/login', methods=['GET', 'POST'])
@utils.with_dbsession
def login():
  db_session = request.db_session
  errors = []
  if request.method == 'POST':
    user_name = request.form['user_name']
    user_password = request.form['user_password']
    user = User.get_by(db_session, user_name, utils.hash_pw(user_password))
    if user:
      # XXX User login keys rather than storing the password hash
      # in a cookie. See issue #16.
      session['user_name'] = user.name
      session['user_passhash'] = user.passhash
      return redirect(url_for('dashboard'))
    errors.append('Username or password invalid.')
  return render_template('login.html', errors=errors)


@app.route('/logout')
@utils.with_dbsession
def logout():
  session.pop('user_name', '')
  session.pop('user_passhash', '')
  return redirect(url_for('dashboard'))


@app.route('/repo/<path:path>')
@utils.requires_auth
@utils.with_dbsession
def view_repo(path):
  session = request.db_session
  repo = get_target_for(session, path)
  if not isinstance(repo, Repository):
    return abort(404)
  return render_template('view_repo.html', user=request.user, repo=repo)


@app.route('/build/<path:path>')
@utils.requires_auth
@utils.with_dbsession
def view_build(path):
  session = request.db_session
  build = get_target_for(session, path)
  if not isinstance(build, Build):
    return abort(404)

  restart = request.args.get('restart', '').strip().lower() == 'true'
  if restart:
    if build.status != Build.Status_Building:
      build.delete()
      build.status = Build.Status_Queued
      request.db_session.add(build)
      request.db_session.commit()
      enqueue(build)
    return redirect(build.url())

  stop = request.args.get('stop', '').strip().lower() == 'true'
  if stop:
    if build.status == Build.Status_Queued:
      build.status = Build.Status_Stopped
    elif build.status == Build.Status_Building:
      terminate_build(build)
    return redirect(build.url())

  return render_template('view_build.html', user=request.user, build=build)


@app.route('/edit/repo', methods=['GET', 'POST'], defaults={'repo_id': None})
@app.route('/edit/repo/<int:repo_id>', methods=['GET', 'POST'])
@utils.requires_auth
@utils.with_dbsession
def edit_repo(repo_id):
  session = request.db_session
  if not request.user.can_manage:
    return abort(403)
  if repo_id is not None:
    repo = session.query(Repository).get(repo_id)
  else:
    repo = None

  errors = []
  if request.method == 'POST':
    secret = request.form.get('repo_secret', '')
    clone_url = request.form.get('repo_clone_url', '')
    repo_name = request.form.get('repo_name', '').strip()
    ref_whitelist = request.form.get('repo_ref_whitelist', '')
    if len(repo_name) < 3 or repo_name.count('/') != 1:
      errors.append('Invalid repository name. Format must be owner/repo')
    if not clone_url:
      errors.append('No clone URL specified')
    other = session.query(Repository).filter_by(name=repo_name).one_or_none()
    if (other and not repo) or (other and other.id != repo.id):
      errors.append('Repository {!r} already exists'.format(repo_name))
    if not errors:
      if not repo:
        repo = Repository(name=repo_name, clone_url=clone_url, secret=secret,
          build_count=0, ref_whitelist=ref_whitelist)
      else:
        repo.name = repo_name
        repo.clone_url = clone_url
        repo.secret = secret
        repo.ref_whitelist = ref_whitelist
      session.add(repo)
      session.commit()
      return redirect(repo.url())

  return render_template('edit_repo.html', user=request.user, repo=repo, errors=errors)


@app.route('/user/new', defaults={'user_id': None}, methods=['GET', 'POST'])
@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
@utils.requires_auth
@utils.with_dbsession
def edit_user(user_id):
  session = request.db_session
  cuser = None
  if user_id is not None:
    cuser = session.query(User).get(user_id)
    if not cuser:
      return abort(404)
    if cuser.id != request.user.id and not request.user.can_manage:
      return abort(403)
  elif not request.user.can_manage:
    return abort(403)

  errors = []
  if request.method == 'POST':
    if not cuser and not request.user.can_manage:
      return abort(403)

    user_name = request.form.get('user_name')
    password = request.form.get('user_password')
    can_manage = request.form.get('user_can_manage') == 'on'
    can_view_buildlogs = request.form.get('user_can_view_buildlogs') == 'on'
    can_download_artifacts = request.form.get('user_can_download_artifacts') == 'on'

    if not cuser:  # Create a new user
      assert request.user.can_manage
      other = session.query(User).filter_by(name=user_name).one_or_none()
      if other:
        errors.append('User {!r} already exists'.format(user_name))
      else:
        cuser = User(name=user_name, passhash=utils.hash_pw(password),
          can_manage=can_manage, can_view_buildlogs=can_view_buildlogs,
          can_download_artifacts=can_download_artifacts)
    else:  # Update user settings
      if password:
        cuser.passhash = utils.hash_pw(password)
      # The user can only update privileges if he has managing privileges.
      if request.user.can_manage:
        cuser.can_manage = can_manage
        cuser.can_view_buildlogs = can_view_buildlogs
        cuser.can_download_artifacts = can_download_artifacts
    if not errors:
      session.add(cuser)
      session.commit()
      return redirect(cuser.url())

  return render_template('edit_user.html', user=request.user, cuser=cuser,
    errors=errors)


@app.route('/download/<int:build_id>/<string:data>')
@utils.requires_auth
@utils.with_dbsession
def download(build_id, data):
  if data not in (Build.Data_Artifact, Build.Data_Log):
    return abort(404)
  build = request.db_session.query(Build).get(build_id)
  if not build or not build.exists(data):
    return abort(404)

  if data == Build.Data_Artifact and not request.user.can_download_artifacts:
    return abort(403)
  if data == Build.Data_Log and not request.user.can_view_buildlogs:
    return abort(403)

  mime = 'application/zip' if data == Build.Data_Artifact else 'text/plain'
  return utils.stream_file(build.path(data), mime=mime)


@app.route('/delete')
@utils.requires_auth
@utils.with_dbsession
def delete():
  repo_id = request.args.get('repo_id', '')
  build_id = request.args.get('build_id', '')
  user_id = request.args.get('user_id', '')

  session = request.db_session
  delete_target = None
  if build_id:
    delete_target = session.query(Build).get(build_id)
    if not request.user.can_manage:
      return abort(403)
  elif repo_id:
    delete_target = session.query(Repository).get(repo_id)
    if not request.user.can_manage:
      return abort(403)
  elif user_id:
    delete_target = session.query(User).get(user_id)
    if delete_target and delete_target.id != request.user.id and not request.user.can_manage:
      return abort(403)

  if not delete_target:
    return abort(404)

  try:
    session.delete(delete_target)
    session.commit()
  except Build.CanNotDelete as exc:
    session.rollback()
    utils.flash(str(exc))
    referer = request.headers.get('Referer', url_for('dashboard'))
    return redirect(referer)

  utils.flash('{} deleted'.format(type(delete_target).__name__))
  return redirect(url_for('dashboard'))
