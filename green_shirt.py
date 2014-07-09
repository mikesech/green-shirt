#!/usr/bin/python

IMAP_HOST = XXX_CONFIGURE_ME
USERNAME =  XXX_CONFIGURE_ME
PASSWORD =  XXX_CONFIGURE_ME

IFTTT_FOOTER = "IFTTT\r\n\r\n\tvia Personal Recipe"

import imaplib, email, email.parser, re, httplib, urllib, subprocess, sys, quopri, string
from time import sleep

def filter_ifttt_footer(text):
  i = string.rfind(text, IFTTT_FOOTER)
  return text[:i] if i > -1 else text

def extract_text_body(msg):
  for part in msg.walk():
    if part.get_content_type() == "text/plain":
      return quopri.decodestring(part.get_payload())
  return None
  
def text_to_mp3(text):
  text = text.strip()
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

def text_to_many_mp3s(text):
  x = text[:]
  mp3s = []
  while len(x) > 0:
    if len(x) > 100:
      a = x[:100]
      # TODO: don't remove the last word if x[100] is not alphanumeric
      m = re.search(r'\W\w*$', a)
      if m is None:
        x = x[100:]
      else:
        size = m.start()
        a = x[:size]
        x = x[size:]
    else:
      a = x
      x = []
    mp3s.append(text_to_mp3(a))
  return mp3s

def play_mp3_from_memory(mp3):
  p = subprocess.Popen(["/usr/bin/mpg123", "-"], stdin=subprocess.PIPE)
  p.communicate(input=mp3)
  p.wait()
def play_many_mp3s_from_memory(mp3s):
  for m in mp3s:
    play_mp3_from_memory(m)

def speak_text(text):
  mp3s = text_to_many_mp3s(text)
  play_many_mp3s_from_memory(mp3s)

def handle_message(subject, body):
  if re.search(r'\[GREEN SHIRT\]', subject) is None:
    print "skipping message: %s" % subject
  else:
    body = filter_ifttt_footer(body)
    print "new message: %s" % body
    try:
      speak_text(body)
    except Exception as e:
      print >> sys.stderr, "error playing message: %s" % str(e)

def process_imap_results(M, data):
  items = data[0].split()
  print >> sys.stderr, "processing %d items" % len(items)
  for num in items:
    typ, data = M.fetch(num, '(RFC822)')
    msg = email.parser.Parser().parsestr(data[0][1])
    
    subject = msg['subject']
    body = extract_text_body(msg)
    
    if body is not None:
      handle_message(subject, body)

def main():
  M = imaplib.IMAP4(IMAP_HOST)
  #M = imaplib.IMAP4_SSL(IMAP_HOST)
  M.login(USERNAME, PASSWORD)
  M.select()
  while True:
#    typ, data = M.search(None, '(UNSEEN SUBJECT "GREEN SHIRT")')
    typ, data = M.search(None, '(UNSEEN)')
    if typ == "OK":
      process_imap_results(M, data)
    else:
      print >> sys.stderr, "error searching imap"
    
    sleep(60)
  M.close()
  M.logout()


if __name__ == "__main__":
  try:
    main()
  except KeyboardInterrupt:
    exit(0)
