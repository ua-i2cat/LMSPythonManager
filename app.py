import urllib3
import sqlite3

from flask import (
  Flask,
  request,
  render_template,
  redirect,
  url_for,
  g
)

from multimediaManager import MultimediaManager

app = Flask(__name__)
mul = MultimediaManager('127.0.0.1', 7777)
database = 'mitsu.db'

def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect(database)
  return db

@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()

def init_db():
  with app.app_context():
    db = get_db()
    cur = db.cursor()
    cur.execute('DROP TABLE IF EXISTS frame_stats')
    cur.execute('CREATE TABLE frame_stats('
      'blackout int, blockloss real,'
      'blur real, contrast real,'
      'exposure real, flickering real,'
      'freezing int, interlace real,'
      'letterbox real, noise real,'
      'pillarbox real, slicing real,'
      'SA real, TA real,'
      'time int PRIMARY KEY)')
    db.commit()

def insert_qoe_json(table, json):
  if not isinstance(json, list):
    raise Exception('provided data must be an array of measurements')

  with app.app_context():
    db = get_db()
    lastrow = None
    for measure in json:
      fields = ['time']
      values = [measure['time']]
      fields += list(measure['fields'].keys())
      values += list(measure['fields'].values())
      insert(db, table, fields, values)
    db.commit()
    return db.cursor().lastrowid

def insert(db, table, fields=(), values=()):
  cur = db.cursor()
  query = 'INSERT INTO %s (%s) VALUES (%s)' % (
    table,
    ', '.join(fields),
    ', '.join(['?'] * len(values))
  )
  cur.execute(query, values)


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

@app.route('/setprofile', methods=['POST'])
def setprofile():
  cProf = mul.getActiveProfiles()
  actProf = []
  for idx, profile in enumerate(cProf):
    if str(idx) in request.form:
      if 'Activate' == request.form[str(idx)]:
        actProf.append(idx)
    elif profile['active']:
      actProf.append(idx)

  if not len(actProf):
    return render_template('index.html', error="There must be at list one active representation")

  mul.setRepresentations(actProf)
  profiles = mul.getActiveProfiles()

  if len(profiles) > 0:
    return render_template('profiles.html', prof=profiles)

  mul.resetPipe()
  return render_template('index.html', error="No active profiles, pipe reseted")

@app.route('/qoemonitor', methods=['POST'])
def qoe_insert():
  json = request.json
  if not json:
    raise Exception('mime type must application/json to insert data')

  lastrow = insert_qoe_json(json)

if __name__ == '__main__':
  init_db()
  app.run(debug=True)

