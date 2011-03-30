#!/usr/bin/python
from xml.dom.minidom import parseString
from xml.parsers.expat import ExpatError
from datetime import datetime, tzinfo, timedelta

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
  text = text.strip()
  try:
    dom = parseString(text)
  except ExpatError:
    return []
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
