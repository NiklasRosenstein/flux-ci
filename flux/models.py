# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

import enum

from sqlalchemy import create_engine
from sqlalchemy import Column, Boolean, Integer, Enum, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from . import config

engine = create_engine(config.db_url, encoding=config.db_encoding)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(Base):
  __tablename__ = 'users'

  id = Column(Integer, primary_key=True)
  name = Column(String)
  passhash = Column(String)
  can_manage = Column(Boolean)
  can_download_artifacts = Column(Boolean)
  can_view_buildlogs = Column(Boolean)

  def __repr__(self):
    return '<User(id={!r}, name={!r})>'.format(self.id, self.name)


class Repository(Base):
  ''' Represents a repository for which push events are being accepted.
  The Git server specified at the ``clone_url`` must accept the Flux
  server's public key. '''

  __tablename__ = 'repos'

  id = Column(Integer, primary_key=True)
  name = Column(String)
  secret = Column(String)
  clone_url = Column(String)
  builds = relationship("Build", back_populates="repo")


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
  Status = [Status_Queued, Status_Building, Status_Error, Status_Error]

  id = Column(Integer, primary_key=True)
  repo_id = Column(Integer, ForeignKey('repos.id'))
  repo = relationship("Repository", back_populates="builds")
  commit_sha = Column(String)
  uuid = Column(String)
  status = Column(Enum(*Status))


Base.metadata.create_all(engine)
