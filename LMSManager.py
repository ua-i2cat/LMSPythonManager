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
    """LMSManager constructor

    It creates a new istance of the LMSManager.

    Args:
      host: The host in which the LiveMediaStreamer is running.
      port: The port in which the LiveMediaStreamer is listening. 
    """
    self.host = host
    self.port = port

  def testConnection(self):
    """Tests the connectivity of this LMSManager instance

    It creates a TCP client sockect connection the specified **IP** and **port**.
    Right after getting a successful connection the socket is closed again. 
    In case of failure logs a message to stderr.

    Returns:
      True if the socket connection was successful, False otherwhise. 
    """
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
    """Sends events to a remote LiveMediaStreamer service.

    Sends a list of events to a remote LiveMediaStreamer service.
    Each execution of sendEvents prints in stdout a JSON representation
    of the events that were sent. The socket is opened and closed for
    each execution.

    Args:
      eJson: it is a dictionary that contains a list of events, each element
      of the list is another dictionary containing all the parameters of 
      an specific event.

    Returns:
      A dictionary containing the return value of the LiveMediaStreamer. It 
      is used only for debbuing purposes.

    Raises:
      Exception: LiveMediaStreamer returned an error message. The message is 
      included in the Exception. 
    """
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
    """Gets the current state of the LiveMediaStreamer service.

    Gets a dictionary containig the list of filters and paths. For each
    filter its own status is included.

    Returns:
      A dictionary describing the LiveMediaStreamer state.  Uses the following
      pattern:
        
        {'filters': [*-list of filters with the current status of each one-*], 'paths': [*-list of paths-*]}

    Raises:
      Exception: LiveMediaStreamer returned an error message. The message is 
      included in the Exception. 
    """
    eJson = {'events': [{'action': 'getState', 'params': {}}]}
    return self.sendEvents(eJson)

  def createFilter(self, fId, fType):
    """Sends an event to create a filter.

    Sends an event to create a filter of the specified type and with the given ID. 

    Args: 
      fId: An integer representing the ID of the filter to create, fId must be unique
      within the whole pipe.
      fType: An string representing the type of the filter to create. Available types are listed
      in **Types.hh** file within the LiveMediaStreamer code. 

    Returns:
      A dictionary containing the return value of the LiveMediaStreamer. It 
      is used only for debbuing purposes.

    Raises:
      Exception: LiveMediaStreamer returned an error message. The message is 
      included in the Exception. 
    """
    params = {'id': fId, 'type': fType}
    event = {'action': 'createFilter', 'params': params} 
    eJson = {'events': [event]}

    return self.sendEvents(eJson)

  def removePath(self, pId):
    """Sends an event to delete the path with the specified ID.

    Sends an event to remove path with the specified ID. All related filters
    will get disconnected and all orphan filters (filters not used in any other 
    path) deleted.

    Args: 
      pId: An integer representing the ID of the path to remove.  

    .. warning: 
      This method is not stable as it should, be careful while using it, it might cause
      LiveMediaStreamer service failures.
    """
    params = {'id': pId}
    event = {'action': 'removePath', 'params': params} 
    eJson = {'events': [event]}

    try:
      return self.sendEvents(eJson)
    except Exception as e:
      logging.error("Error removing path: " + str(e))

  def removeFilter(self, fId):
    """Sends an event to delete the filter with he specified ID.

    Sends an event to remove the filter with the specified. It will be removed
    only if the filter is not used in any other path.

    Args: 
      fId: An integer representing the ID of the filter to remove.  
    """
    params = {'id': fId}
    event = {'action': 'removeFilter', 'params': params} 
    eJson = {'events': [event]}

    try:
      return self.sendEvents(eJson)
    except Exception as e:
      logging.error("Error removing filter: " + str(e))

  def createPath(self, pId, orgFilterId, dstFilterId, orgWriterId, dstReaderId, filtersIds):
    """Sends an event to create a new path.

    Sends an event to create a new path with the specified filters, reader and writer. 

    Args: 
      pId: An integer representing the ID of the new path to create. 
      orgFilterId: The ID of the filter in which the path starts.
      dstfilterId: The ID of the filter in which the path ends. 
      orgWriterId: The ID of the writer to be used in origin filter.
      dstReaderId: The ID of the reader to be used in destination filter.

    Returns:
      A dictionary containing the return value of the LiveMediaStreamer. It 
      is used only for debbuing purposes.

    Raises:
      Exception: LiveMediaStreamer returned an error message. The message is 
      included in the Exception. 
    """
    params = {'id': pId, 'orgFilterId': orgFilterId, 'dstFilterId': dstFilterId, 
        'orgWriterId': orgWriterId, 'dstReaderId': dstReaderId, 'midFiltersIds': filtersIds}

    event = {'action': 'createPath', 'params': params} 
    eJson = {'events': [event]}

    return self.sendEvents(eJson)
        
  def stop(self):
    """Stops the current pipe.

    It deletes all paths and filters, so the pipe is completeley cleared.
    """
    eJson = {'events': [{'action': 'stop', 'params':{}}]}

    try:
      return self.sendEvents(eJson)
    except Exception as e:
      logging.error("Error stopping pipe: " + str(e))

  def filterEvent(self, fId, action, params):
    """Sends an event to a filter.

    Sends the specified event to the specified filter. 

    Args: 
      fId: An integer representing the ID of the filter.
      action: An string specifiying the action to trigger.
      params: A dictionary containing all the parameters related to the specified
      action of the specified filter.

    Returns:
      A dictionary containing the return value of the LiveMediaStreamer. It 
      is used only for debbuing purposes.

    Raises:
      Exception: LiveMediaStreamer returned an error message. The message is 
      included in the Exception. 
    """
    eJson = {'events': [{'action': action, 'filterId': fId, 'params': params}]}
    return self.sendEvents(eJson)


