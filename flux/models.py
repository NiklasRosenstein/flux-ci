
"""
This package provides the database models using PonyORM.
"""

from flask import url_for
from flux import app, config, utils

import datetime
import hashlib
import os
import pony.orm as orm
import shutil
import uuid

db = orm.Database(**config.database)
session = orm.db_session
commit = orm.commit
rollback = orm.rollback
select = orm.select
desc = orm.desc


class User(db.Entity):
  _table_ = 'users'

  id = orm.PrimaryKey(int)
  name = orm.Required(str, unique=True)
  passhash = orm.Required(str)
  can_manage = orm.Required(bool)
  can_download_artifacts = orm.Required(bool)
  can_view_buildlogs = orm.Required(bool)
  login_tokens = orm.Set('LoginToken')

  def set_password(self, password):
    self.passhash = utils.hash_pw(password)

  @classmethod
  def get_by_login_details(cls, user_name, password):
    passhash = utils.hash_pw(password)
    return orm.select(x for x in cls if x.name == user_name and
                        x.passhash == passhash).first()

  @classmethod
  def get_root_user(cls):
    return orm.select(x for x in cls if x.name == config.root_user).first()

  @classmethod
  def create_or_update_root(cls):
    root = cls.get_root_user()
    if root:
      # Make sure the root has all privileges.
      root.can_manage = True
      root.can_download_artifacts = True
      root.can_view_buildlogs = True
      root.set_password(config.root_password)
      root.name = config.root_user
    else:
      # Create a new root user.
      app.logger.info('Creating new root user: {!r}'.format(config.root_user))
      root = cls(
        name=config.root_user,
        passhash=utils.hash_pw(config.root_password),
        can_manage=True,
        can_download_artifacts=True,
        can_view_buildlogs=True)
    return root

  def url(self):
    return url_for('edit_user', user_id=self.id)


class LoginToken(db.Entity):
  """
  A login token represents the credentials that we can savely store in the
  browser's session and it will not reveal any information about the users
  password. For additional security, a login token is bound to the IP that
  the user logged in from an has an expiration date.

  The expiration duration can be set with the `login_token_duration`
  configuration value. Setting this option to #None will prevent tokens
  from expiring.
  """

  _table_ = 'logintokens'

  id = orm.PrimaryKey(int)
  ip = orm.Required(str)
  user = orm.Required(User)
  token = orm.Required(str, unique=True)
  created = orm.Required(datetime.datetime)

  @classmethod
  def create(cls, ip, user):
    " Create a new login token assigned to the specified IP and user. "

    created = datetime.datetime.now()
    token = str(uuid.uuid4()).replace('-', '')
    token += hashlib.md5((token + str(created)).encode()).hexdigest()
    return cls(ip=ip, user=user, token=token, created=created)

  def expired(self):
    " Returns #True if the token is expired, #False otherwise. "

    if config.login_token_duration is None:
      return False
    now = datetime.datetime.now()
    return (self.created + config.login_token_duration) < now


class Repository(db.Entity):
  """
  Represents a repository for which push events are being accepted. The Git
  server specified at the `clone_url` must accept the Flux server's public
  key.
  """

  _table_ = 'repos'

  id = orm.PrimaryKey(int)
  name = orm.Required(str)
  secret = orm.Required(str)
  clone_url = orm.Required(str)
  build_count = orm.Required(int, default=0)
  builds = orm.Set('Build')
  ref_whitelist = orm.Optional(str)  # newline separated list of accepted Git refs

  def url(self, **kwargs):
    return url_for('view_repo', path=self.name, **kwargs)

  def check_accept_ref(self, ref):
    whitelist = list(filter(bool, self.ref_whitelist.split('\n')))
    if not whitelist or ref in whitelist:
      return True
    return False

  def validate_ref_whitelist(self, value, oldvalue, initiator):
    return '\n'.join(filter(bool, (x.strip() for x in value.split('\n'))))

  def most_recent_build(self):
    return self.builds.select().order_by(desc(Build.date_started)).first()


class Build(db.Entity):
  """
  Represents a build that is generated on a push to a repository. The build is
  initially queued and then processed when a slot is available. The build
  directory is generated from the configured root directory and the build
  #uuid. The log file has the exact same path with the `.log` suffix appended.

  After the build is complete (whether successful or errornous), the build
  directory is zipped and the original directory is removed.
  """

  _table_ = 'builds'

  Status_Queued = 'queued'
  Status_Building = 'building'
  Status_Error = 'error'
  Status_Success = 'success'
  Status_Stopped = 'stopped'
  Status = [Status_Queued, Status_Building, Status_Error, Status_Success, Status_Stopped]

  Data_BuildDir = 'build_dir'
  Data_OverrideDir = 'override_dir'
  Data_Artifact = 'artifact'
  Data_Log = 'log'

  class CanNotDelete(Exception):
    pass

  id = orm.PrimaryKey(int)
  repo = orm.Required(Repository, column='repo_id')
  ref = orm.Required(str)
  commit_sha = orm.Required(str)
  num = orm.Required(int)
  status = orm.Required(str)  # One of the Status strings
  date_queued = orm.Required(datetime.datetime, default=datetime.datetime.now)
  date_started = orm.Optional(datetime.datetime)
  date_finished = orm.Optional(datetime.datetime)

  def __init__(self, **kwargs):
    # Backwards compatibility for when SQLAlchemy was used, Auto Increment
    # was not enabled there.
    if 'id' not in kwargs:
      kwargs['id'] = orm.max(x.id for x in Build) + 1
    super(Build, self).__init__(**kwargs)

  def url(self, data=None, **kwargs):
    path = self.repo.name + '/' + str(self.num)
    if not data:
      return url_for('view_build', path=path, **kwargs)
    elif data in (self.Data_Artifact, self.Data_Log):
      return url_for('download', build_id=self.id, data=data, **kwargs)
    else:
      raise ValueError('invalid mode: {!r}'.format(mode))

  def path(self, data=Data_BuildDir):
    base = os.path.join(config.build_dir, self.repo.name.replace('/', os.sep), str(self.num))
    if data == self.Data_BuildDir:
      return base
    elif data == self.Data_Artifact:
      return base + '.zip'
    elif data == self.Data_Log:
      return base + '.log'
    elif data == self.Data_OverrideDir:
      return os.path.join(config.override_dir, self.repo.name.replace('/', os.sep))
    else:
      raise ValueError('invalid value for "data": {!r}'.format(data))

  def exists(self, data):
    return os.path.exists(self.path(data))

  def log_contents(self):
    path = self.path(self.Data_Log)
    if os.path.isfile(path):
      with open(path, 'r') as fp:
        return fp.read()
    return None

  def check_download_permission(self, data, user):
    if data == self.Data_Artifact:
      return user.can_download_artifacts and (
        self.status == self.Status_Success or user.can_view_buildlogs)
    elif data == self.Data_Log:
      return user.can_view_buildlogs
    else:
      raise ValueError('invalid value for data: {!r}'.format(data))

  def delete_build(self):
    if self.status == self.Status_Building:
      raise self.CanNotDelete('can not delete build in progress')
    try:
      os.remove(self.path(self.Data_Artifact))
    except OSError as exc:
      app.logger.exception(exc)
    try:
      os.remove(self.path(self.Data_Log))
    except OSError as exc:
      app.logger.exception(exc)

  # db.Entity Overrides

  def before_delete(self):
    self.delete_build()


def get_target_for(path):
  """
  Given an URL path, returns either a #Repository or #Build that the path
  identifies. #None will be retunred if the path points to an unknown
  repository or build.

  Examples:

      /User/repo    => Repository(User/repo)
      /User/repo/1  => Build(1, Repository(User/repo))
  """

  parts = path.split('/')
  if len(parts) not in (2, 3):
    return None
  repo_name = parts[0] + '/' + parts[1]
  repo = Repository.get(name=repo_name)
  if not repo:
    return None
  if len(parts) == 3:
    try: num = int(parts[2])
    except ValueError: return None
    return Build.get(repo=repo, num=num)
  return repo


db.generate_mapping(create_tables=False)  # TODO
