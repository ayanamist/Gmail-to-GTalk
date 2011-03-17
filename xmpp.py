#!/usr/bin/python
import config
import oauth
import mail

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import xmpp, urlfetch
from db import User, Session, Mail

class chat_handler(webapp.RequestHandler):
  def post(self):
    try:
      message = xmpp.Message(self.request.POST)
    except xmpp.InvalidMessageError:
      return
    content = message.body
    if not content:
      return
    self._jid = message.sender.split('/')[0]
    args = content.strip().split(' ')
    try:
      func = getattr(self, args[0].lower())
    except AttributeError, e:
      message.reply(e.message)
    else:
      result = func(*args[1:])
      if result:
        message.reply(result)

  def oauth(self, mobile=None):
    consumer = oauth.OAuthConsumer(config.OAUTH_CONSUMER_KEY, config.OAUTH_CONSUMER_SECRET)
    params = {'xoauth_displayname': 'Gmail2GTalk', 'scope': config.RESOURCE_URL}
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, callback='oob', parameters=params,
                                                               http_url=config.REQUEST_TOKEN_URL)
    signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
    oauth_request.sign_request(signature_method_hmac_sha1, consumer, None)
    try:
      result = urlfetch.fetch(oauth_request.to_url(), method=oauth_request.http_method)
    except urlfetch.Error:
      return 'Network Error!'
    token = oauth.OAuthToken.from_string(result.content)
    s = Session.get_by_key_name(self._jid)
    if not s:
      Session(key_name=self._jid, data=result.content).put()
    else:
      s.data = result.content
      s.put()
    if mobile == 'mobile':
      params = {'btmpl': 'mobile'}
    else:
      params = None
    oauth_request = oauth.OAuthRequest.from_token_and_callback(token, http_url=config.AUTHORIZATION_URL,
                                                               parameters=params)
    url = oauth_request.to_url()
    return 'Please visit following url to authorize:\n%s' % url

  def bind(self, verifier):
    s = Session.get_by_key_name(self._jid)
    if s:
      token = oauth.OAuthToken.from_string(s.data)
      consumer = oauth.OAuthConsumer(config.OAUTH_CONSUMER_KEY, config.OAUTH_CONSUMER_SECRET)
      oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, verifier=verifier,
                                                                 http_url=config.ACCESS_TOKEN_URL)
      signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
      oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)
      try:
        result = urlfetch.fetch(oauth_request.to_url(), method=oauth_request.http_method)
      except urlfetch.Error:
        return 'Network Error!'
      try:
        token = oauth.OAuthToken.from_string(result.content)
      except BaseException:
        return 'Wrong verifier!'
      u = User.get_by_key_name(self._jid)
      if u:
        u.access_key = token.key
        u.access_secret = token.secret
        u.put()
      else:
        User(key_name=self._jid, access_key=token.key, access_secret=token.secret).put()
      s.data = None
      s.put()
      return 'Successfully bind your account.'

  def remove(self):
    u = User.get_by_key_name(self._jid)
    if u:
      u.access_key = None
      u.access_secret = None
      u.enabled = False
      u.put()
      s = Session.get_by_key_name(self._jid)
      if s:
        s.delete()
      return 'Successfully remove your account.'

  def pause(self):
    u = User.get_by_key_name(self._jid)
    if u:
      u.enabled = False
      u.put()
      s = Session.get_by_key_name(self._jid)
      if s:
        s.delete()
      return 'Gmail notification is paused.'

  def resume(self):
    u = User.get_by_key_name(self._jid)
    if u:
      u.enabled = True
      u.put()
      try:
        presence = xmpp.get_presence(self._jid)
      except xmpp.Error:
        presence = False
      if presence:
        try:
          Session(key_name=self._jid).put()
        except db.BadKeyError:
          pass
      return 'Gmail notification is resumed.'

  def check(self):
    u = User.get_by_key_name(self._jid)
    if not u:
      return 'Please bind your account first.'
    emails_map = mail.get_mails(u.access_key, u.access_secret)
    emails = list()
    for email in emails_map:
      str = 'From: %(author)s\nTitle: %(title)s\nSummary: %(summary)s\nTime: %(time)s\n%(url)s' % email
      emails.insert(0, str)
      if db.WRITE_CAPABILITY:
        try:
          Mail(key_name=email['id']).put()
        except db.BadKeyError:
          pass
    if emails:
      return '\n\n'.join(emails)
    else:
      return 'No new emails.'


class available_handler(webapp.RequestHandler):
  def post(self):
    jid = self.request.get('from').split('/')[0]
    if User.get_by_key_name(jid):
      try:
        Session(key_name=jid).put()
      except db.BadKeyError:
        pass


class unavailable_handler(webapp.RequestHandler):
  def post(self):
    jid = self.request.get('from').split('/')[0]
    s = Session.get_by_key_name(jid)
    if s:
      u = User.get_by_key_name(jid)
      if u:
        try:
          presence = xmpp.get_presence(jid)
        except xmpp.Error:
          presence = False
        if not presence:
          s.delete()
      else:
        s.delete()


def main():
  application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', chat_handler),
                                        ('/_ah/xmpp/presence/available/', available_handler),
                                        ('/_ah/xmpp/presence/unavailable/', unavailable_handler)])
  run_wsgi_app(application)

if __name__ == "__main__":
  main()