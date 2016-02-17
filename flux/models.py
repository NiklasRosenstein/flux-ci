# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import os, shutil

from sqlalchemy import create_engine, desc
from sqlalchemy import Column, Boolean, Integer, Enum, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship

from . import config, utils
from .model_base import Base, Session
from flask import url_for

engine = create_engine(config.db_url, encoding=config.db_encoding)
Session = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


class User(Base):
  __tablename__ = 'users'

  id = Column(Integer, primary_key=True)
  name = Column(String, unique=True)
  passhash = Column(String)
  can_manage = Column(Boolean)
  can_download_artifacts = Column(Boolean)
  can_view_buildlogs = Column(Boolean)

  def __repr__(self):
    return '<User(id={!r}, name={!r})>'.format(self.id, self.name)

  @classmethod
  def root_user(cls, session):
    return session.query(cls).filter_by(name=config.root_user).one_or_none()

  @classmethod
  def create_root_if_not_exists(cls, session):
    root = cls.root_user(session)
    if root:
      # Make sure the root has all privileges.
      root.can_manage = True
      root.can_download_artifacts = True
      root.can_view_buildlogs = True
    else:
      # Create a new root user.
      print(' * [flux] creating new root user: {!r}'.format(config.root_user))
      root = cls(name=config.root_user, passhash=utils.hash_pw(config.root_password),
        can_manage=True, can_download_artifacts=True, can_view_buildlogs=True)
    session.add(root)
    return root

  def url(self):
    return url_for('edit_user', user_id=self.id)

  @classmethod
  def get_by(cls, session, user_name, passhash):
    return session.query(cls).filter_by(name=user_name, passhash=passhash).one_or_none()


class Repository(Base):
  ''' Represents a repository for which push events are being accepted.
  The Git server specified at the ``clone_url`` must accept the Flux
  server's public key. '''

  __tablename__ = 'repos'

  id = Column(Integer, primary_key=True)
  name = Column(String)
  secret = Column(String)
  clone_url = Column(String)
  build_count = Column(Integer)
  builds = relationship("Build", back_populates="repo",
    order_by=lambda: desc(Build.num), cascade='all, delete-orphan')
  ref_whitelist = Column(String)  # ; separated list of accepted refs

  def url(self, **kwargs):
    return url_for('view_repo', path=self.name, **kwargs)

  def check_accept_ref(self, ref):
    whitelist = list(filter(bool, self.ref_whitelist.split('\n')))
    if not whitelist or ref in whitelist:
      return True
    return False

  def validate_ref_whitelist(self, value, oldvalue, initiator):
    return '\n'.join(filter(bool, (x.strip() for x in value.split('\n'))))


class Build(Base):
  ''' Represents a build that is generated on a push to a
  repository. The build is initially queued and then processed
  when a slot is available. The build directory is generated
  from the configured root directory and the build :attr:`uuid`.
  The log file has the exact same path with the ``.log``
  suffix appended. After the build is complete (whether
  successful or errornous), the build directory is zipped and
  the original directory is removed. '''

  __tablename__ = 'builds'

  Status_Queued = 'queued'
  Status_Building = 'building'
  Status_Error = 'error'
  Status_Success = 'success'
  Status_Stopped = 'stopped'
  Status = [Status_Queued, Status_Building, Status_Error, Status_Success, Status_Stopped]

  Data_BuildDir = 'build_dir'
  Data_Artifact = 'artifact'
  Data_Log = 'log'

  class CanNotDelete(Exception):
    pass

  id = Column(Integer, primary_key=True)
  repo_id = Column(Integer, ForeignKey('repos.id'))
  repo = relationship("Repository", back_populates="builds", lazy='joined')
  ref = Column(String)
  commit_sha = Column(String)
  num = Column(Integer)
  status = Column(Enum(*Status))
  date_queued = Column(DateTime)
  date_started = Column(DateTime)
  date_finished = Column(DateTime)

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

  def delete(self):
    if self.status == self.Status_Building:
      raise self.CanNotDelete('can not delete build in progress')
    try:
      os.remove(self.path(self.Data_Artifact))
    except OSError as exc:
      print(exc)
    try:
      os.remove(self.path(self.Data_Log))
    except OSError as exc:
      print(exc)


def get_target_for(session, path):
  ''' Given a path, returns either a :class:`Repository` or :class:`Build`
  based on the format and value. Returns None if the path is invalid or
  the repository or build does not exist. '''

  parts = path.split('/')
  if len(parts) not in (2, 3):
    return None
  repo_name = parts[0] + '/' + parts[1]
  repo = session.query(Repository).filter_by(name=repo_name).one_or_none()
  if not repo:
    return None
  if len(parts) == 3:
    try: num = int(parts[2])
    except ValueError: return None
    return session.query(Build).filter_by(repo=repo, num=num).one_or_none()
  return repo


def get_public_key():
  ''' Returns the servers SSH public key. '''

  # XXX Support all valid options and eventually parse the config file?
  filename = config.ssh_identity_file or os.path.expanduser('~/.ssh/id_rsa')
  if not filename.endswith('.pub'):
    filename += '.pub'
  if os.path.isfile(filename):
    with open(filename) as fp:
      return fp.read()
  return None


Base.metadata.create_all(engine)
