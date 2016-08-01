import urllib3

from flask import Flask, request, render_template, redirect, url_for
from multimediaManager import MultimediaManager


app = Flask(__name__)
mul = MultimediaManager('127.0.0.1', 7777)

@app.route('/')
def home():
  if mul.testConnection():
    return render_template('index.html')
  else:
    return render_template('connection.html')

@app.route('/connect', methods=['POST'])
def connect():
  global mul
  domain = request.form['domain']
  port = request.form['port']

  try:
    port = int(port)
  except ValueError:
    return render_template('connection.html', error="Port must be an integer value")

  mul = MultimediaManager(domain, port)
  return redirect(url_for('home'))

@app.route('/start', methods=['POST'])
def start():
  source = request.form['source']
  basename = request.form['basename']
  segduration = request.form['segduration']

  try:
      uri = urllib3.util.url.parse_url(source)
  except AttributeError:
    # It seams old versions of urllib3 do not have url submodule
    uri = urllib3.util.parse_url(uri) 
  except:
    return render_template('index.html', error="Cannot parse the given URL") 

  if uri.scheme != 'rtsp' and uri.scheme != 'rtmp':
    return render_template('index.html', error="It must be an RTSP or RTMP URL")

  try:
    segduration = int(segduration)
  except ValueError:
    return render_template('index.html', error="Segment duration must be an integer, values are in seconds")
  
  mul.resetPipe()
  try:
    mul.configureDasher('/tmp', basename, segduration, 4, segduration*3)
  except:
    mul.resetPipe()
    return render_template('index.html', error="Failed configuring dasher")

  try:
    if uri.scheme == 'rtsp':
      mul.addRTSPSource(source)
  except Exception as e:
    mul.resetPipe()
    return render_template('index.html', error="Failed adding source: {0}".format(e))

  profiles = mul.getActiveProfiles()

  if len(profiles) > 0:
    return render_template('profiles.html', prof=profiles)

  mul.resetPipe()
  return render_template('index.html', error="No active profiles, pipe reseted") 

if __name__ == '__main__':
  app.run(debug=True)

