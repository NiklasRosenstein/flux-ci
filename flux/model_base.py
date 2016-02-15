# Copyright (C) 2016  Niklas Rosenstein
# All rights reserved.

from sqlalchemy import event
from sqlalchemy.orm import session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta


class OrmEventMetaClass(DeclarativeMeta):
  ''' This is a metaclass for SQLAlchemy models that registers `ORM
  events`_ if certain methods on the class are available. Supported
  methods are:

  * ``validate_X(value, oldvalue, initiator)`` where ``X`` stands
    for a column name, invoked by the ``set`` ORM event
  * ``save()`` invoked by the ``before_insert`` and ``before_update``
    ORM events
  * ``delete()`` invoked by the ``before_delete`` ORM event

  .. _ORM Events: http://docs.sqlalchemy.org/en/latest/orm/events.html
  '''

  def __init__(cls, name, bases, data):
    super().__init__(name, bases, data)

    # validate_~() method -- Used to validate when a parameter is set.
    for key in dir(cls):
      if key.startswith('validate_'):
        attr_name = key[len('validate_'):]
        attr = getattr(cls, attr_name, None)
        if isinstance(attr, InstrumentedAttribute):
          def callback(target, value, oldvalue, initiator):
            return getattr(target, key)(value, oldvalue, initiator)
          event.listen(attr, 'set', callback, retval=True)

    # save() method -- Used in before_update and before_insert.
    if hasattr(cls, 'save'):
      @event.listens_for(cls, 'before_update')
      @event.listens_for(cls, 'before_insert')
      def callback(mapper, connection, target):
        target.save()

    # delete() method -- Used in before_delete.
    if hasattr(cls, 'delete'):
      @event.listens_for(cls, 'before_delete')
      def callback(mapper, connection, target):
        target.delete()


class Session(session.Session):
  ''' Custom session that implements the context-manager interface. '''

  def __enter__(self):
    return self

  def __exit__(self, exc_value, exc_type, exc_tb):
    try:
      if exc_value is not None:
        self.rollback()
      else:
        self.commit()
    finally:
      self.close()


Base = declarative_base(metaclass=OrmEventMetaClass)
