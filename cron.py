#!/usr/bin/python
import mail

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import xmpp, urlfetch_errors
from db import Session, Mail, User

class cron_handler(webapp.RequestHandler):
  def get(self):
    if db.WRITE_CAPABILITY:
      q = dict()
      for u in Session.all().filter('data =', None):
        jid = u.key().name()
        u = User.get_by_key_name(jid)
        rpc = mail.get_mails(u.access_key, u.access_secret, async=True)
        q[jid] = rpc
      while q:
        jid, rpc = q.popitem()
        try:
          result = rpc.get_result()
        except urlfetch_errors.Error:
          continue
        else:
          emails_map = mail.parse(result.content)
          emails = list()
          for email in emails_map:
            if not Mail.get_by_key_name(email['id']):
              str = 'From: %(author)s\nTitle: %(title)s\nSummary: %(summary)s\nTime: %(time)s\n%(url)s' % email
              emails.insert(0, str)
              Mail(key_name=email['id']).put()
          if emails:
            xmpp.send_message(jid, '\n\n'.join(emails))


def main():
  application = webapp.WSGIApplication([('/cron', cron_handler)])
  run_wsgi_app(application)

if __name__ == "__main__":
  main()