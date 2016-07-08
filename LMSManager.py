"""
LMSManager.py - This is a controller for a remote LMS instance
 
Copyright (C) 2016  Fundació i2CAT, Internet i Innovació digital a Catalunya

This file is part of media-streamer.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

Authors: David Cassany <david.cassany@i2cat.net>  
"""

import socket
import logging
import json

class LMSManager:
  sock = None
  BUFFER_SIZE = 65536

  def __init__(self, host, port):
    self.host = host
    self.port = port

  def testConnection(self):
    res = True
    try:
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.sock.connect((self.host, self.port))
    except socket.error:
      logging.error('couldn\'t connect to {} host and {} port'.format(*[self.host, self.port]))
      res = False
    finally:
      self.sock.close()
      self.sock = None

    return res

  def sendEvents(self, eJson):
    res = None
    try:
      self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.sock.connect((self.host, self.port))
      self.sock.send(json.dumps(eJson).encode())
      res = self.sock.recv(self.BUFFER_SIZE)
    except socket.error:
      logging.error('couldn\'t connect to {} host and {} port'.format(*[self.host, self.port]))
    finally:
      self.sock.close()
      self.sock = None

    if res != None:
      res = json.loads(res.decode())
      
      if 'error' in res and res['error'] != None:
        raise Exception(res['error'])

    print(json.dumps(eJson))

    return res

  def getState(self):
    eJson = {'events': [{'action': 'getState', 'params': {}}]}
    return self.sendEvents(eJson)

  def createFilter(self, fId, fType):
    params = {'id': fId, 'type': fType}
    event = {'action': 'createFilter', 'params': params} 
    eJson = {'events': [event]}

    return self.sendEvents(eJson)

  def removePath(self, pId):
    params = {'id': pId}
    event = {'action': 'removePath', 'params': params} 
    eJson = {'events': [event]}

    try:
      return self.sendEvents(eJson)
    except Exception as e:
      print("Error removing path: " + str(e))

  def removeFilter(self, pId):
    params = {'id': pId}
    event = {'action': 'removeFilter', 'params': params} 
    eJson = {'events': [event]}

    try:
      return self.sendEvents(eJson)
    except Exception as e:
      print("Error removing filter: " + str(e))

  def createPath(self, pId, orgFilterId, dstFilterId, orgWriterId, dstReaderId, filtersIds):
    params = {'id': pId, 'orgFilterId': orgFilterId, 'dstFilterId': dstFilterId, 'orgWriterId': orgWriterId, 'dstReaderId': dstReaderId, 'midFiltersIds': filtersIds}
    event = {'action': 'createPath', 'params': params} 
    eJson = {'events': [event]}

    return self.sendEvents(eJson)
        
  def stop(self):
    eJson = {'events': [{'action': 'stop', 'params':{}}]}

    try:
      return self.sendEvents(eJson)
    except Exception as e:
      print("Error stopping pipe: " + str(e))

  def filterEvent(self, fId, action, params):
    eJson = {'events': [{'action': action, 'filterId': fId, 'params': params}]}
    return self.sendEvents(eJson)


