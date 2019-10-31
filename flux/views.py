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

from flux import app, config, file_utils, models, utils
from flux.build import enqueue, terminate_build
from flux.models import User, LoginToken, Repository, Build, get_target_for, select, desc
from flux.utils import secure_filename
from flask import request, session, redirect, url_for, render_template, abort
from datetime import datetime

import json
import os
import uuid

API_GOGS = 'gogs'
API_GITHUB = 'github'
API_GITEA = 'gitea'
API_GITBUCKET = 'gitbucket'
API_BITBUCKET = 'bitbucket'
API_BITBUCKET_CLOUD = 'bitbucket-cloud'
API_GITLAB = 'gitlab'
API_BARE = 'bare'

@app.route('/hook/push', methods=['POST'])
@utils.with_io_response(mimetype='text/plain')
@utils.with_logger()
@models.session
def hook_push(logger):
  ''' PUSH event webhook. The URL parameter ``api`` must be specified
  for Flux to expect the correct JSON payload format. Supported values
  for ``api`` are

  * ``gogs``
  * ``github``
  * ``gitea``
  * ``gitbucket``
  * ``bitbucket``
  * ``bitbucket-cloud``
  * ``gitlab``
  * ``bare``

  If no or an invalid value is specified for this parameter, a 400
  Invalid Request response is generator. '''

  api = request.args.get('api')
  if api not in (API_GOGS, API_GITHUB, API_GITEA, API_GITBUCKET, API_BITBUCKET, API_BITBUCKET_CLOUD, API_GITLAB, API_BARE):
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
    secret = utils.get(data, 'secret', str)
    get_repo_secret = lambda r: r.secret
  elif api == API_GITHUB:
    event = request.headers.get('X-Github-Event')
    if event != 'push':
      logger.error("Payload rejected (expected 'push' event, got {!r})".format(event))
      return 400
    owner = utils.get(data, 'repository.owner.name', str)
    name = utils.get(data, 'repository.name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'after', str)
    secret = request.headers.get('X-Hub-Signature', '').replace('sha1=', '')
    get_repo_secret = lambda r: utils.get_github_signature(r.secret, request.data)
  elif api == API_GITEA:
    event = request.headers.get('X-Gitea-Event')
    if event != 'push':
      logger.error("Payload rejected (expected 'push' event, got {!r})".format(event))
      return 400
    owner = utils.get(data, 'repository.owner.username', str)
    name = utils.get(data, 'repository.name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'after', str)
    secret = utils.get(data, 'secret', str)
    get_repo_secret = lambda r: r.secret
  elif api == API_GITBUCKET:
    event = request.headers.get('X-Github-Event')
    if event != 'push':
      logger.error("Payload rejected (expected 'push' event, got {!r})".format(event))
      return 400
    owner = utils.get(data, 'repository.owner.login', str)
    name = utils.get(data, 'repository.name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'after', str)
    secret = request.headers.get('X-Hub-Signature', '').replace('sha1=', '')
    if secret:
      get_repo_secret = lambda r: utils.get_github_signature(r.secret, request.data)
    else:
      get_repo_secret = lambda r: r.secret
  elif api == API_BITBUCKET:
    event = request.headers.get('X-Event-Key')
    if event != 'repo:refs_changed':
      logger.error("Payload rejected (expected 'repo:refs_changed' event, got {!r})".format(event))
      return 400
    owner = utils.get(data, 'repository.project.name', str)
    name = utils.get(data, 'repository.name', str)
    ref = utils.get(data, 'changes.0.refId', str)
    commit = utils.get(data, 'changes.0.toHash', str)
    secret = request.headers.get('X-Hub-Signature', '').replace('sha256=', '')
    if secret:
      get_repo_secret = lambda r: utils.get_bitbucket_signature(r.secret, request.data)
    else:
      get_repo_secret = lambda r: r.secret
  elif api == API_BITBUCKET_CLOUD:
    event = request.headers.get('X-Event-Key')
    if event != 'repo:push':
      logger.error("Payload rejected (expected 'repo:push' event, got {!r})".format(event))
      return 400
    owner = utils.get(data, 'repository.project.project', str)
    name = utils.get(data, 'repository.name', str)

    ref_type = utils.get(data, 'push.changes.0.new.type', str)
    ref_name = utils.get(data, 'push.changes.0.new.name', str)
    ref = "refs/" + ("heads/" if ref_type == "branch" else "tags/") + ref_name

    commit = utils.get(data, 'push.changes.0.new.target.hash', str)
    secret = None
    get_repo_secret = lambda r: r.secret
  elif api == API_GITLAB:
    event = utils.get(data, 'object_kind', str)
    if event != 'push' and event != 'tag_push':
      logger.error("Payload rejected (expected 'push' or 'tag_push' event, got {!r})".format(event))
      return 400
    owner = utils.get(data, 'project.namespace', str)
    name = utils.get(data, 'project.name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'checkout_sha', str)
    secret = request.headers.get('X-Gitlab-Token')
    get_repo_secret = lambda r: r.secret
  elif api == API_BARE:
    owner = utils.get(data, 'owner', str)
    name = utils.get(data, 'name', str)
    ref = utils.get(data, 'ref', str)
    commit = utils.get(data, 'commit', str)
    secret = utils.get(data, 'secret', str)
    get_repo_secret = lambda r: r.secret
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
  if secret == None:
    secret = ''

  name = owner + '/' + name

  repo = Repository.get(name=name)
  if not repo:
    logger.error('PUSH event rejected (unknown repository)')
    return 400
  if get_repo_secret(repo) != secret:
    logger.error('PUSH event rejected (invalid secret)')
    return 400
  if not repo.check_accept_ref(ref):
    logger.info('Git ref {!r} not whitelisted. No build dispatched'.format(ref))
    return 200

  build = Build(
    repo=repo,
    commit_sha=commit,
    num=repo.build_count,
    ref=ref,
    status=Build.Status_Queued,
    date_queued=datetime.now(),
    date_started=None,
    date_finished=None)
  repo.build_count += 1

  models.commit()
  enqueue(build)
  logger.info('Build #{} for repository {} queued'.format(build.num, repo.name))
  logger.info(utils.strip_url_path(config.app_url) + build.url())
  return 200


@app.route('/')
@models.session
@utils.requires_auth
def dashboard():
  context = {}
  context['builds'] = select(x for x in Build).order_by(desc(Build.date_queued)).limit(10)
  context['user'] = request.user
  return render_template('dashboard.html', **context)


@app.route('/repositories')
@models.session
@utils.requires_auth
def repositories():
  repositories = select(x for x in Repository).order_by(Repository.name)
  return render_template('repositories.html', user=request.user, repositories=repositories)


@app.route('/users')
@models.session
@utils.requires_auth
def users():
  if not request.user.can_manage:
    return abort(403)
  users = select(x for x in User)
  return render_template('users.html', user=request.user, users=users)


@app.route('/integration')
@models.session
@utils.requires_auth
def integration():
  if not request.user.can_manage:
    return abort(403)
  return render_template('integration.html', user=request.user, public_key=utils.get_public_key())


@app.route('/login', methods=['GET', 'POST'])
@models.session
def login():
  errors = []
  if request.method == 'POST':
    user_name = request.form['user_name']
    user_password = request.form['user_password']
    if user_name and user_password:
      user = User.get(name=user_name, passhash=utils.hash_pw(user_password))
      if user:
        token = LoginToken.create(request.remote_addr, user)
        session['flux_login_token'] = token.token
        return redirect(url_for('dashboard'))
    errors.append('Username or password invalid.')
  return render_template('login.html', errors=errors)


@app.route('/logout')
@models.session
@utils.requires_auth
def logout():
  if request.login_token:
    request.login_token.delete()
  session.pop('flux_login_token')
  return redirect(url_for('dashboard'))


@app.route('/repo/<path:path>')
@models.session
@utils.requires_auth
def view_repo(path):
  repo = get_target_for(path)
  if not isinstance(repo, Repository):
    return abort(404)

  context = {}
  page_size = 10

  try:
    context['page_number'] = int(request.args.get('page', 1))
  except ValueError:
    context['page_number'] = 1

  page_from = (context['page_number'] - 1) * page_size
  page_to = page_from + page_size

  context['next_page'] = None if context['page_number'] <= 1 else context['page_number'] - 1
  context['previous_page'] = None if len(repo.builds) <= page_to else context['page_number'] + 1
  context['builds'] = repo.builds.select().order_by(desc(Build.date_queued))[page_from:page_to]
  return render_template('view_repo.html', user=request.user, repo=repo, **context)


@app.route('/repo/generate-keypair/<path:path>')
@models.session
@utils.requires_auth
def generate_keypair(path):
  if not request.user.can_manage:
    return abort(403)

  repo = get_target_for(path)
  if not isinstance(repo, Repository):
    return abort(404)

  session['errors'] = []

  utils.makedirs(utils.get_customs_path(repo))

  try:
    private_key, public_key = utils.generate_ssh_keypair(repo.name + '@FluxCI')
    private_key_path = utils.get_repo_private_key_path(repo)
    public_key_path = utils.get_repo_public_key_path(repo)

    try:
      file_utils.create_file_path(private_key_path)
      file_utils.create_file_path(public_key_path)

      file_utils.write_file(private_key_path, private_key)
      file_utils.write_file(public_key_path, public_key)

      try:
        os.chmod(private_key_path, 0o600)
        utils.flash('SSH keypair generated.')
      except BaseException as exc:
        app.logger.info(exc)
        session['errors'].append('Could not set permissions to newly generated private key.')
    except BaseException as exc:
      app.logger.info(exc)
      session['errors'].append('Could not save generated SSH keypair.')
  except BaseException as exc:
    app.logger.info(exc)
    session['errors'].append('Could not generate new SSH keypair.')

  return redirect(url_for('edit_repo', repo_id = repo.id))


@app.route('/repo/remove-keypair/<path:path>')
@models.session
@utils.requires_auth
def remove_keypair(path):
  if not request.user.can_manage:
    return abort(403)

  repo = get_target_for(path)
  if not isinstance(repo, Repository):
    return abort(404)

  session['errors'] = []

  private_key_path = utils.get_repo_private_key_path(repo)
  public_key_path = utils.get_repo_public_key_path(repo)

  try:
    file_utils.delete(private_key_path)
    file_utils.delete(public_key_path)
    utils.flash('SSH keypair removed.')
  except BaseException as exc:
    app.logger.info(exc)
    session['errors'].append('Could not remove SSH keypair.')

  return redirect(url_for('edit_repo', repo_id = repo.id))


@app.route('/build/<path:path>')
@models.session
@utils.requires_auth
def view_build(path):
  build = get_target_for(path)
  if not isinstance(build, Build):
    return abort(404)

  restart = request.args.get('restart', '').strip().lower() == 'true'
  if restart:
    if build.status != Build.Status_Building:
      build.delete_build()
      build.status = Build.Status_Queued
      build.date_started = None
      build.date_finished = None
      models.commit()
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
@models.session
@utils.requires_auth
def edit_repo(repo_id):
  if not request.user.can_manage:
    return abort(403)
  if repo_id is not None:
    repo = Repository.get(id=repo_id)
  else:
    repo = None

  errors = []

  context = {}
  if repo and repo.name:
    if os.path.isfile(utils.get_repo_public_key_path(repo)):
      try:
        context['public_key'] = file_utils.read_file(utils.get_repo_public_key_path(repo))
      except BaseException as exc:
        app.logger.info(exc)
        errors.append('Could not read public key for this repository.')

  if request.method == 'POST':
    secret = request.form.get('repo_secret', '')
    clone_url = request.form.get('repo_clone_url', '')
    repo_name = request.form.get('repo_name', '').strip()
    ref_whitelist = request.form.get('repo_ref_whitelist', '')
    build_script = request.form.get('repo_build_script', '')
    if len(repo_name) < 3 or repo_name.count('/') != 1:
      errors.append('Invalid repository name. Format must be owner/repo')
    if not clone_url:
      errors.append('No clone URL specified')
    other = Repository.get(name=repo_name)
    if (other and not repo) or (other and other.id != repo.id):
      errors.append('Repository {!r} already exists'.format(repo_name))
    if not errors:
      if not repo:
        repo = Repository(
          name=repo_name,
          clone_url=clone_url,
          secret=secret,
          build_count=0,
          ref_whitelist=ref_whitelist)
      else:
        repo.name = repo_name
        repo.clone_url = clone_url
        repo.secret = secret
        repo.ref_whitelist = ref_whitelist
      try:
        utils.write_override_build_script(repo, build_script)
      except BaseException as exc:
        app.logger.info(exc)
        errors.append('Could not make change on build script')
      if not errors:
        return redirect(repo.url())

  return render_template('edit_repo.html', user=request.user, repo=repo, errors=errors, **context)


@app.route('/user/new', defaults={'user_id': None}, methods=['GET', 'POST'])
@app.route('/user/<int:user_id>', methods=['GET', 'POST'])
@models.session
@utils.requires_auth
def edit_user(user_id):
  cuser = None
  if user_id is not None:
    cuser = User.get(id=user_id)
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
      other = User.get(name=user_name)
      if other:
        errors.append('User {!r} already exists'.format(user_name))
      elif len(user_name) == 0:
        errors.append('Username is empty')
      elif len(password) == 0:
        errors.append('Password is empty')
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
      return redirect(cuser.url())
    models.rollback()

  return render_template('edit_user.html', user=request.user, cuser=cuser,
    errors=errors)


@app.route('/download/<int:build_id>/<string:data>')
@models.session
@utils.requires_auth
def download(build_id, data):
  if data not in (Build.Data_Artifact, Build.Data_Log):
    return abort(404)
  build = Build.get(id=build_id)
  if not build:
    return abort(404)
  if not build.check_download_permission(data, request.user):
    return abort(403)
  if not build.exists(data):
    return abort(404)
  mime = 'application/zip' if data == Build.Data_Artifact else 'text/plain'
  download_name = "{}-{}.{}".format(build.repo.name.replace("/", "_"), build.num, "zip" if data == Build.Data_Artifact else 'log')
  return utils.stream_file(build.path(data), name=download_name, mime=mime)


@app.route('/delete')
@models.session
@utils.requires_auth
def delete():
  repo_id = request.args.get('repo_id', '')
  build_id = request.args.get('build_id', '')
  user_id = request.args.get('user_id', '')

  delete_target = None
  return_to = 'dashboard'
  if build_id:
    delete_target = Build.get(id=build_id)
    return_to = delete_target.repo.url()
    if not request.user.can_manage:
      return abort(403)
  elif repo_id:
    delete_target = Repository.get(id=repo_id)
    return_to = url_for('repositories')
    if not request.user.can_manage:
      return abort(403)
  elif user_id:
    delete_target = User.get(id=user_id)
    return_to = url_for('users')
    if delete_target and delete_target.id != request.user.id and not request.user.can_manage:
      return abort(403)

  if not delete_target:
    return abort(404)

  try:
    delete_target.delete()
  except Build.CanNotDelete as exc:
    models.rollback()
    utils.flash(str(exc))
    referer = request.headers.get('Referer', return_to)
    return redirect(referer)

  utils.flash('{} deleted'.format(type(delete_target).__name__))
  return redirect(return_to)


@app.route('/build')
@models.session
@utils.requires_auth
def build():
  repo_id = request.args.get('repo_id', '')
  ref_name = request.args.get('ref', '')
  if not repo_id or not ref_name:
    return abort(400)
  if not request.user.can_manage:
    return abort(403)

  commit = '0' * 32
  repo = Repository.get(id=repo_id)
  build = Build(
    repo=repo,
    commit_sha=commit,
    num=repo.build_count,
    ref=ref_name,
    status=Build.Status_Queued,
    date_queued=datetime.now(),
    date_started=None,
    date_finished=None)
  repo.build_count += 1

  models.commit()
  enqueue(build)
  return redirect(repo.url())

@app.route('/ping-repo', methods=['POST'])
@models.session
@utils.requires_auth
def ping_repo():
  repo_url = request.form.get('url')
  repo_name = request.form.get('repo')

  repo = type('',(object,),{'name' : repo_name})()

  res = utils.ping_repo(repo_url, repo)
  if (res == 0):
    return 'ok', 200
  else:
    return 'fail', 404


@app.route('/overrides/list/<path:path>')
@models.session
@utils.requires_auth
def overrides_list(path):
  if not request.user.can_manage:
    return abort(403)

  separator = "/"
  errors = []
  errors = errors + session.pop('errors', [])
  context = {}

  repo_path, context['overrides_path'] = file_utils.split_url_path(path)
  context['repo'] = get_target_for(repo_path)
  context['list_path'] = url_for('overrides_list', path = path)
  context['edit_path'] = url_for('overrides_edit', path = path)
  context['delete_path'] = url_for('overrides_delete', path = path)
  context['download_path'] = url_for('overrides_download', path = path)
  context['upload_path'] = url_for('overrides_upload', path = path)
  if context['overrides_path'] != '' and context['overrides_path'] != None:
    context['parent_name'] = separator.join(context['overrides_path'].split(separator)[:-1])
    context['parent_path'] = url_for('overrides_list', path = separator.join(path.split(separator)[:-1]))

  if not isinstance(context['repo'], Repository):
    return abort(404)

  try:
    cwd = os.path.join(utils.get_override_path(context['repo']), context['overrides_path'].replace('/', os.sep))
    utils.makedirs(os.path.dirname(cwd))
    context['files'] = file_utils.list_folder(cwd)
  except BaseException as exc:
    app.logger.info(exc)
    errors.append('Could not read overrides for this repository.')

  return render_template('overrides_list.html', user=request.user, **context, errors=errors)


@app.route('/overrides/edit/<path:path>', methods=['GET', 'POST'])
@models.session
@utils.requires_auth
def overrides_edit(path):
  if not request.user.can_manage:
    return abort(403)

  separator = "/"
  context = {}
  errors = []

  repo_path, context['overrides_path'] = file_utils.split_url_path(path)
  context['repo'] = get_target_for(repo_path)
  if not isinstance(context['repo'], Repository):
    return abort(404)

  file_path = os.path.join(utils.get_override_path(context['repo']), context['overrides_path'].replace('/', os.sep))

  if request.method == 'POST':
    override_content = request.form.get('override_content')
    try:
      file_utils.write_file(file_path, override_content)
      utils.flash('Changes in file was saved.')
    except BaseException as exc:
      app.logger.info(exc)
      errors.append('Could not write into file.')

  dir_path_parts = path.split("/")
  context['dir_path'] = separator.join(dir_path_parts[:-1])

  try:
    context['content'] = file_utils.read_file(file_path)
  except BaseException as exc:
    app.logger.info(exc)
    errors.append('Could not read file.')

  return render_template('overrides_edit.html', user=request.user, **context, errors=errors)


OVERRIDES_ACTION_CREATEFOLDER = 'createNewFolder'
OVERRIDES_ACTION_CREATEFILE = 'createNewFile'
OVERRIDES_ACTION_RENAME = 'rename'


@app.route('/overrides/delete/<path:path>')
@models.session
@utils.requires_auth
def overrides_delete(path):
  if not request.user.can_manage:
    return abort(403)

  separator = "/"

  repo_path, overrides_path = file_utils.split_url_path(path)
  repo = get_target_for(repo_path)
  if not isinstance(repo, Repository):
    return abort(404)

  return_path_parts = path.split(separator)
  return_path = separator.join(return_path_parts[:-1])
  cwd = os.path.join(utils.get_override_path(repo), overrides_path.replace('/', os.sep))

  session['errors'] = []
  try:
    file_utils.delete(cwd)
    utils.flash('Object was deleted.')
  except BaseException as exc:
    app.logger.info(exc)
    session['errors'].append('Could not delete \'' + return_path_parts[-1] + '\'.')

  return redirect(url_for('overrides_list', path = return_path))


@app.route('/overrides/download/<path:path>')
@models.session
@utils.requires_auth
def overrides_download(path):
  if not request.user.can_manage:
    return abort(403)

  repo_path, overrides_path = file_utils.split_url_path(path)
  repo = get_target_for(repo_path)
  if not isinstance(repo, Repository):
    return abort(404)

  file_path = os.path.join(utils.get_override_path(repo), overrides_path.replace('/', os.sep))
  return utils.stream_file(file_path, mime='application/octet-stream')


@app.route('/overrides/upload/<path:path>', methods=['GET', 'POST'])
@models.session
@utils.requires_auth
def overrides_upload(path):
  if not request.user.can_manage:
    return abort(403)

  separator = "/"
  context = {}
  errors = [] + session.pop('errors', [])

  repo_path, context['overrides_path'] = file_utils.split_url_path(path)
  repo = get_target_for(repo_path)
  if not isinstance(repo, Repository):
    return abort(404)

  context['list_path'] = url_for('overrides_list', path = path)
  cwd = os.path.join(utils.get_override_path(repo), context['overrides_path'].replace('/', os.sep))

  if request.method == 'POST':
    session['errors'] = []
    files = request.files.getlist('upload_file')
    if not files:
      utils.flash('No file was uploaded.')
    else:
      file_uploads = []
      for file in files:
        filepath = os.path.join(cwd, secure_filename(file.filename))
        try:
          file.save(filepath)
          file_uploads.append("File '{}' was uploaded.".format(file.filename))
        except BaseException as exc:
          app.logger.info(exc)
          session['errors'].append("Could not upload '{}'.".format(file.filename))
      utils.flash(" ".join(file_uploads))
      if not session['errors']:
        return redirect(url_for('overrides_list', path = path))

  dir_path_parts = path.split("/")
  context['dir_path'] = separator.join(dir_path_parts[:-1])

  return render_template('overrides_upload.html', user=request.user, **context, errors=errors)


@app.route('/overrides/<string:action>')
@models.session
@utils.requires_auth
def overrides_actions(action):
  if not request.user.can_manage:
    return abort(403)

  separator = "/"
  session['errors'] = []
  repo_id = request.args.get('repo_id', '')
  path = request.args.get('path', '')

  repo = Repository.get(id=repo_id)
  if not repo:
    return abort(404)

  if action == OVERRIDES_ACTION_CREATEFOLDER:
    name = secure_filename(request.args.get('name', ''))
    try:
      file_utils.create_folder(os.path.join(utils.get_override_path(repo), path.replace('/', os.sep)), name)
      utils.flash('Folder was created.')
      return redirect(url_for('overrides_list', path = separator.join([repo.name, path, name]).replace('//', '/')))
    except BaseException as exc:
      app.logger.info(exc)
      session['errors'].append('Could not create folder.')
      return redirect(url_for('overrides_list', path = separator.join([repo.name, path]).replace('//', '/')))
  elif action == OVERRIDES_ACTION_CREATEFILE:
    name = secure_filename(request.args.get('name', ''))
    try:
      file_utils.create_file(os.path.join(utils.get_override_path(repo), path.replace('/', os.sep)), name)
      utils.flash('File was created.')
      return redirect(url_for('overrides_edit', path = separator.join([repo.name, path, name]).replace('//', '/')))
    except BaseException as exc:
      app.logger.info(exc)
      session['errors'].append('Could not create file.')
      return redirect(url_for('overrides_list', path = separator.join([repo.name, path]).replace('//', '/')))
  elif action == OVERRIDES_ACTION_RENAME:
    name = request.args.get('name', '').replace('../', '')
    original_name = request.args.get('original_name', '').replace('../', '')
    new_path = os.path.join(utils.get_override_path(repo), path.replace('/', os.sep), name)
    original_path = os.path.join(utils.get_override_path(repo), path.replace('/', os.sep), original_name)

    try:
      file_utils.rename(original_path, new_path)
      utils.flash('Object was renamed.')
    except BaseException as exc:
      app.logger.info(exc)
      session['errors'].append('Could not rename \'' + original_name + '\'.')
    return redirect(url_for('overrides_list', path = separator.join([repo.name, path]).replace('//', '/')))

  return abort(404)


@app.errorhandler(403)
def error_403(e):
  return render_template('403.html'), 403


@app.errorhandler(404)
def error_404(e):
  return render_template('404.html'), 404


@app.errorhandler(500)
def error_500(e):
  return render_template('500.html'), 500
