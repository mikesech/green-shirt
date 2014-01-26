#!/usr/bin/python

IMAP_HOST = XXX_CONFIGURE_ME
USERNAME =  XXX_CONFIGURE_ME
PASSWORD =  XXX_CONFIGURE_ME

import imaplib, email, email.parser, re, httplib, urllib, subprocess, sys, quopri
from yaml import dump

def extract_text_body(msg):
  for part in msg.walk():
    if part.get_content_type() == "text/plain":
      return quopri.decodestring(part.get_payload())
  return None
  
def text_to_mp3(text):
  if len(text) > 100:
    print >> sys.stderr, "warning: text too long"
    text = text[:100]
  conn = httplib.HTTPConnection("translate.google.com")
  headers = {"Referer": "http://translate.google.com/", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0)"}
  params = urllib.urlencode({
    'ie': 'UTF-8',
    'tl': 'en',
    'total': 1,
    'idx': 0,
    'prev': 'input',
    'textlen': len(text),
    'q': text
  })
  url = "/translate_tts?%s" % params
  conn.request("GET", url, "", headers)
  response = conn.getresponse()
  if response.status != 200:
    raise StandardError("Bad status querying Google: %i (%s)" % (response.status, response.reason))
  return response.read()

def play_mp3_from_memory(mp3):
  p = subprocess.Popen(["/usr/bin/mpg123", "-"], stdin=subprocess.PIPE)
  p.communicate(input=mp3)
  p.wait()

def speak_text(text):
  mp3 = text_to_mp3(text)
  play_mp3_from_memory(mp3)

def handle_message(body):
  print "new message: %s" % body
  try:
    speak_text(body)
  except Exception as e:
    print >> sys.stderr, "error playing message: %s" % str(e)

M = imaplib.IMAP4(IMAP_HOST)
M.login(USERNAME, PASSWORD)M.select()
typ, data = M.search(None, '(UNSEEN SUBJECT "GREEN SHIRT")')
for num in data[0].split():
  typ, data = M.fetch(num, '(RFC822)')
  msg = email.parser.Parser().parsestr(data[0][1])
  
  subject = msg['subject']
  body = extract_text_body(msg)
  
  if body is not None:
    handle_message(body)
  M.store(num, '+FLAGS', '\Seen')
M.close()
M.logout()