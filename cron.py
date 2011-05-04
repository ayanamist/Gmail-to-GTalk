#!/usr/bin/python
import config
import oauth

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import xmpp, urlfetch
from google.appengine.api.capabilities import CapabilitySet
from db import Session, Mail, User
from mail import parse

class cron_handler(webapp.RequestHandler):
  def get(self):
    def handle_result(rpc):
      try:
        result = rpc.get_result()
      except urlfetch.Error:
        return
      else:
        jid = self.jids[id(rpc)]
        emails_map = parse(result.content)
        emails = list()
        for email in emails_map:
          if not Mail.get_by_key_name(email['id']):
            if Mail(key_name=email['id']).put():
              str = 'From: %(author)s\nTitle: %(title)s\nSummary: %(summary)s\nTime: %(time)s\n%(url)s' % email
              emails.insert(0, str)
        if emails:
          while CapabilitySet('xmpp').is_enabled():
            try:
              xmpp.send_message(jid, '\n\n'.join(emails))
            except xmpp.Error:
              pass
            else:
              break

    def create_callback(rpc):
      return lambda: handle_result(rpc)

    if not db.WRITE_CAPABILITY:
      return
    rpcs = []
    self.jids = {}
    for u in Session.all().filter('data =', None):
      jid = u.key().name()
      u = User.get_by_key_name(jid)
      token = oauth.OAuthToken(u.access_key, u.access_secret)
      consumer = oauth.OAuthConsumer(config.OAUTH_CONSUMER_KEY, config.OAUTH_CONSUMER_SECRET)
      oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_url=config.RESOURCE_URL)
      signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
      oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)
      rpc = urlfetch.create_rpc()
      rpc.callback = create_callback(rpc)
      urlfetch.make_fetch_call(rpc, oauth_request.http_url, headers=oauth_request.to_header())
      rpcs.append(rpc)
      self.jids[id(rpc)] = jid
    for rpc in rpcs:
      rpc.wait()


def main():
  application = webapp.WSGIApplication([('/cron', cron_handler)])
  run_wsgi_app(application)

if __name__ == "__main__":
  main()