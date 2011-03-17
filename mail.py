#!/usr/bin/python
import config
import oauth

from xml.dom.minidom import parseString
from datetime import datetime, tzinfo, timedelta
from google.appengine.api import urlfetch

class GMT8Tzinfo(tzinfo):
  def utcoffset(self, date_time):
    return timedelta(hours=8)

  def dst(self, date_time):
    return timedelta(0)

  def tzname(self, date_time):
    return 'GMT +0800'


class UtcTzinfo(tzinfo):
  def utcoffset(self, date_time):
    return timedelta(hours=0)

  def dst(self, date_time):
    return timedelta(0)

  def tzname(self, date_time):
    return 'UTC'


def parse(text):
  def get_text(nodelist):
    for node in nodelist:
      if node.nodeType == node.TEXT_NODE:
        return node.data
    return ''

  emails = []
  dom = parseString(text)
  entries = dom.getElementsByTagName('entry')
  for entry in entries:
    email = dict()
    email['title'] = get_text(entry.getElementsByTagName('title')[0].childNodes)
    email['summary'] = get_text(entry.getElementsByTagName('summary')[0].childNodes)
    email['url'] = entry.getElementsByTagName('link')[0].attributes['href'].value
    time_str = get_text(entry.getElementsByTagName('issued')[0].childNodes).replace('T24:', 'T00:')
    email['time'] = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UtcTzinfo()).astimezone(
      GMT8Tzinfo()).strftime('%Y-%m-%d %H:%M:%S')
    email['id'] = get_text(entry.getElementsByTagName('id')[0].childNodes)
    author = entry.getElementsByTagName('author')[0]
    author_name = get_text(author.getElementsByTagName('name')[0].childNodes)
    author_email = get_text(author.getElementsByTagName('email')[0].childNodes)
    authors = ['%s<%s>' % (author_name, author_email)]
    for c in entry.getElementsByTagName('contributor'):
      author_name = get_text(c.getElementsByTagName('name')[0].childNodes)
      author_email = get_text(c.getElementsByTagName('email')[0].childNodes)
      authors.append('%s<%s>' % (author_name, author_email))
    email['author'] = ', '.join(authors)
    emails.append(email)
  return emails


def get_mails(key, secret, async=False):
  token = oauth.OAuthToken(key, secret)
  consumer = oauth.OAuthConsumer(config.OAUTH_CONSUMER_KEY, config.OAUTH_CONSUMER_SECRET)
  oauth_request = oauth.OAuthRequest.from_consumer_and_token(consumer, token=token, http_url=config.RESOURCE_URL)
  signature_method_hmac_sha1 = oauth.OAuthSignatureMethod_HMAC_SHA1()
  oauth_request.sign_request(signature_method_hmac_sha1, consumer, token)
  if not async:
    result = urlfetch.fetch(oauth_request.http_url, headers=oauth_request.to_header())
    return parse(result.content)
  else:
    rpc = urlfetch.create_rpc()
    urlfetch.make_fetch_call(rpc, oauth_request.http_url, headers=oauth_request.to_header())
    return rpc