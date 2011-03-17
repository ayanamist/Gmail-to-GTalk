#!/usr/bin/python
from google.appengine.ext import db
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError

class MyModel(db.Model):
  def put(self, **kwargs):
    while db.WRITE_CAPABILITY:
      try:
        result = super(MyModel, self).put(**kwargs)
      except (db.Timeout, db.InternalError):
        pass
      except CapabilityDisabledError:
        return None
      else:
        return result
    else:
      return None

  def delete(self, **kwargs):
    while db.WRITE_CAPABILITY:
      try:
        result = super(MyModel, self).delete(**kwargs)
      except (db.Timeout, db.InternalError):
        pass
      except CapabilityDisabledError:
        return None
      else:
        return result
    else:
      return None

  @classmethod
  def get_by_key_name(cls, key_names, parent=None, **kwargs):
    while db.READ_CAPABILITY:
      try:
        result = super(MyModel, cls).get_by_key_name(key_names, parent=parent, **kwargs)
      except (db.Timeout, db.InternalError):
        pass
      else:
        return result
    else:
      return None


class Mail(MyModel):
  pass


class User(MyModel):
  access_key = db.StringProperty()
  access_secret = db.StringProperty()
  enabled = db.BooleanProperty(default=True)


class Session(MyModel):
  data = db.TextProperty(default=None)