"""
SecurityManager.py  - This is a controller for a remote LMS instance
                      for a security scenario
 
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

import time
import math
import urllib3
import os

from . import LMSManager

class SecurityManager:
  lms = None
  DEF_FPS = 25
  DEF_WIDTH = 1280
  DEF_HEIGHT = 720
  DEF_LOOKAHEAD = 4
  DEF_MAX_FPS = 30
  
  def __init__(self, host, port):
    self.lms = LMSManager.LMSManager(host, port)
    self.receiverId = 1
    self.transmitterId = 2
    self.videoEncoderId = 3
    self.videoMixerId = 4
    self.videoResamplerId = 5
    self.videoEncoder2Id = 6
    self.videoMixer2Id = 7
    self.videoResampler2Id = 8
    self.sharedMemoryId = 9
    self.outputPathId = 1
    self.gridPathId = 2
    self.mainOutputStreamId = 1
    self.gridOutputStreamId = 2
    self.grid = False
    
  def startPipe(self, grid = False):
    self.grid = grid
    try:
      self.lms.createFilter(self.receiverId, 'receiver')
      self.lms.createFilter(self.transmitterId, 'transmitter')
      self.lms.createFilter(self.videoEncoderId, 'videoEncoder')
      self.lms.createFilter(self.videoMixerId, 'videoMixer')
      self.lms.createFilter(self.videoResamplerId, 'videoResampler')
      self.lms.createFilter(self.sharedMemoryId, 'sharedMemory')
      if grid:
        self.lms.createFilter(self.videoEncoder2Id, 'videoEncoder')
        self.lms.createFilter(self.videoMixer2Id, 'videoMixer')
        self.lms.createFilter(self.videoResampler2Id, 'videoResampler')
    except:
      self.lms.stop()
      raise Exception("Failed createing filters. Pipe cleared")

    self.lms.filterEvent(self.videoResamplerId, 'configure', {'pixelFormat': 2})
    if grid:
      self.lms.filterEvent(self.videoResampler2Id, 'configure', {'pixelFormat': 2})

    self.lms.filterEvent(self.videoMixerId, 
                         'configure', 
                         {'fps': self.DEF_MAX_FPS, 
                           'width': self.DEF_WIDTH,
                           'height': self.DEF_HEIGHT})
    self.lms.filterEvent(self.videoEncoderId, 'configure', {'fps': self.DEF_FPS, 'lookahead': self.DEF_LOOKAHEAD})

    if grid:
      self.lms.filterEvent(self.videoMixer2Id, 
                           'configure', 
                           {'fps': self.DEF_MAX_FPS, 
                             'width': self.DEF_WIDTH,
                             'height': self.DEF_HEIGHT})
      self.lms.filterEvent(self.videoEncoder2Id, 'configure', {'fps': self.DEF_FPS, 'lookahead': self.DEF_LOOKAHEAD})

    try:
      self.lms.createPath(self.outputPathId, 
                     self.videoMixerId, 
                     self.transmitterId, 
                     -1, self.mainOutputStreamId, 
                     [self.sharedMemoryId, self.videoResamplerId, self.videoEncoderId])

      if grid:
        self.lms.createPath(self.gridPathId, 
                       self.videoMixer2Id, 
                       self.transmitterId, 
                       -1, self.gridOutputStreamId, 
                       [self.videoResampler2Id, self.videoEncoder2Id])

    except: 
      self.lms.stop()
      raise Exception("Failed connecting path. Pipe cleared")

    self.lms.filterEvent(self.transmitterId, 
                         'addRTSPConnection', 
                         {'id': self.mainOutputStreamId, 
                            'name': 'output', 
                            'txFormat': 'std', 
                            'readers': [self.mainOutputStreamId]})
    if grid:
      self.lms.filterEvent(self.transmitterId, 
                           'addRTSPConnection', 
                           {'id': self.gridOutputStreamId, 
                              'name': 'grid', 
                              'txFormat': 'std', 
                              'readers': [self.gridOutputStreamId]})

  def findRecvSessionByPort(self, state, port):
    print("requested port: " + str(port))
    for cFilter in state['filters']:
      if cFilter['id'] == self.receiverId:
        for session in cFilter['sessions']:
          print(session['id'])
          for subsession in session['subsessions']:
            print("session port " + str(subsession['port']))
            if port == subsession['port']:
              return session['id']

    return None

  def resetPipe(self):
    self.stopPipe()
    self.startPipe()

  def getMaxFilterId(self, state):
    maxFilterId = 0
    for cFilter in state['filters']:
      maxFilterId = max(cFilter['id'], maxFilterId)

    return maxFilterId

  def getMaxPathId(self, state):
    maxPathId = 0
    for cPath in state['paths']:
      maxPathId = max(cPath['id'], maxPathId)

    return maxPathId

  def getChannels(self, state, mixId):
    mixerCh = []
    for cFilter in state['filters']:
      if cFilter['id'] == mixId:
        mixerCh = cFilter['channels']

    return mixerCh

  def getMaxVideoChannel(self, state, mixId):
    maxChannelId = 0
    channels = self.getChannels(state, mixId)
    for channel in channels:
      maxChannelId = max(channel['id'], maxChannelId)

    return maxChannelId

  def getVideoMixerSize(self, state, mixId):
    size = None
    for cFilter in state['filters']:
      if cFilter['id'] == mixId:
        size = [cFilter['width'], cFilter['height']]
        break

    return size

  def getPathFromDst(self, state, dstFId, dstRId):
    path = None
    for path in state['paths']:
      if path['destinationFilter'] == dstFId and path['destinationReader'] == dstRId:
        return path

  def getPathsFromDstFilter(self, state, dstFId):
    paths = []
    for path in state['paths']:
      if path['destinationFilter'] == dstFId:
        paths.append(path)

    return paths

  def getFilterType(self, state, fId):
    fType = None
    for cFilter in state['filters']:
      if cFilter['id'] == fId:
        fType = cFilter['type']
        break

    return fType

  def filterExists(self, state, fId):
    for cFilter in state['filters']:
      if cFilter['id'] == fId:
        return True

    return False

  def connectInputSource(self, state, inputFilterId, inputWriterId, raw):
    if not raw:
      decId = self.getMaxFilterId(state) + 1
      resId = decId + 1
    else:
      resId = self.getMaxFilterId(state) + 1
    
    res2Id = resId + 1

    srcPathId = self.getMaxPathId(state) + 1
    mainPathId = srcPathId + 1
    gridPathId = mainPathId + 1

    outputReaderId = self.getMaxVideoChannel(state, self.videoMixerId) + 1

    try:
      if not raw: 
        self.lms.createFilter(decId, "videoDecoder")
      self.lms.createFilter(resId, "videoResampler") 
      if self.grid:
        self.lms.createFilter(res2Id, "videoResampler")
    except: 
      self.lms.removeFilter(resId)
      if not raw:
        self.lms.removeFilter(decId)
      if self.grid:
        self.lms.removeFilter(res2Id)
      raise Exception("Failed creating filters")

    size = self.getVideoMixerSize(state, self.videoMixerId)
    if size == None:
      raise Exception("Could not load main videoMixer size!")

    self.lms.filterEvent(resId, 'configure', {'fps': self.DEF_FPS, 
                                              'pixelFormat': 0,
                                              'width': size[0],
                                              'height': size[1]})

    if self.grid:
      size = self.getVideoMixerSize(state, self.videoMixer2Id)
      if size == None:
        raise Exception("Could not load grid videoMixer size!") 

      channels = self.getChannels(state, self.videoMixer2Id)
      mixCols = math.ceil(math.sqrt(len(channels) + 1))

      self.lms.filterEvent(res2Id, 'configure', {'fps': self.DEF_FPS, 
                                              'pixelFormat': 0,
                                              'width': size[0] // mixCols,
                                              'height': size[1] // mixCols})

    try:
      if not raw:
        self.lms.createPath(srcPathId, 
                            inputFilterId,
                            decId,
                            inputWriterId, -1, [])

        self.lms.createPath(mainPathId, 
                            decId,
                            self.videoMixerId,
                            -1, outputReaderId,
                            [resId])
        if self.grid:
          self.lms.createPath(gridPathId, 
                              decId,
                              self.videoMixer2Id,
                              -1, outputReaderId,
                              [res2Id])

      else:
        self.lms.createPath(mainPathId, 
                            inputFilterId,
                            self.videoMixerId,
                            -1, outputReaderId,
                            [resId])
        if self.grid:
          self.lms.createPath(gridPathId, 
                              inputFilterId,
                              self.videoMixer2Id,
                              -1, outputReaderId,
                              [res2Id])

    except:
      self.lms.removePath(srcPathId)
      self.lms.removePath(mainPathId)
      self.lms.removePath(gridPathId)

      self.lms.removeFilter(resId)
      if not raw:
        self.lms.removeFilter(decId)
      if self.grid:
        self.lms.removeFilter(res2Id)
      raise Exception("Failed creating input paths")

    return outputReaderId

  def getState(self):
    return self.lms.getState()

  def addRTSPSource(self, uri, keepAlive = True):
    state = self.lms.getState()
    if not self.filterExists(state, self.videoMixerId) or not self.filterExists(state, self.transmitterId):
      raise Exception("Is there any pipe ready?")

    if not self.filterExists(state, self.receiverId):
      try:
        self.lms.createFilter(self.receiverId, 'receiver')
      except:
        raise Exception("Failed creating receiver")

    try:
      sourceUrl = urllib3.util.url.parse_url(uri)
    except:
      raise Exception("Cannot parse given url")

    if sourceUrl.scheme != 'rtsp':
      raise Exception("Given url is no RTSP")

    sourceId = os.path.basename(sourceUrl.path)
    if not sourceId:
      raise Exception("Error, given url may have an empty path")

    self.lms.filterEvent(self.receiverId, 'addSession', {'uri': uri, 
                         'progName': '', 'keepAlive': keepAlive, 'id': sourceId})

    port = None
    count = 0
    search = True
    mixerCh = []
    state = None
    while search:
      time.sleep(1)
      state = self.lms.getState()
      for cFilter in state['filters']:
        if cFilter['id'] == self.receiverId:
          for session in cFilter['sessions']:
            if session['id'] == sourceId:
              for subsession in session['subsessions']:
                port = subsession['port']
                search = False

      count += 1
      if count >= 10 and search:
        raise Exception("No successful RTSP negotiation")

    chnl = self.connectInputSource(state, self.receiverId, port, False)
      

    self.commuteChannel(chnl)

    if self.grid:
      self.updateGrid() 

    return chnl

  def addV4LSource(self, device, width, height, fps, pformat = "YUYV", forceformat = True):
    state = self.lms.getState()
    if not self.filterExists(state, self.videoMixerId) or not self.filterExists(state, self.transmitterId):
      raise Exception("Is there any pipe ready?")
        

    capId = self.getMaxFilterId(state) + 1
    
    try:
      self.lms.createFilter(capId, "v4lcapture")
    except:
      raise Exception("Failed creating V4LFilter")

    self.lms.filterEvent(capId, 'configure', {'fps': fps,
                                              'device': device,
                                              'width': width,
                                              'height': height})

    count = 0
    wait = True
    while wait:
      time.sleep(1)
      state = self.lms.getState()
      for cFilter in state['filters']:
        if cFilter['id'] == capId:
          if cFilter['status'] == 'capture':
            wait = False

      count += 1
      if count >= 10 and search:
        raise Exception("No successful V4L filter configuration")

    chnl = self.connectInputSource(state, capId, -1, True)

    self.commuteChannel(chnl)

    if self.grid:
      self.updateGrid()

    return chnl

  def removeInputChannel(self, chnl):
    state = self.lms.getState()

    path = self.getPathFromDst(state, self.videoMixerId, chnl)
    if path != None:
      origFId = path['originFilter']
      self.lms.removePath(path['id'])
      if origFId != self.receiverId and not self.grid:
        paths = self.getPathsFromDstFilter(state, origFId)
        for relatedPath in paths:
          self.lms.removePath(relatedPath['id'])
          if path['originFilter'] == self.receiverId:
            sourceId = self.findRecvSessionByPort(state, relatedPath['originWriter'])
            if sourceId != None:
              self.lms.filterEvent(self.receiverId, 'removeSession', {'id': sourceId})

    if self.grid:
      path = self.getPathFromDst(state, self.videoMixer2Id, chnl)
      if path != None:
        origFId = path['originFilter']
        self.lms.removePath(path['id'])
        if origFId != self.receiverId:
          paths = self.getPathsFromDstFilter(state, origFId)
          for relatedPath in paths:
            self.lms.removePath(relatedPath['id'])
            if relatedPath['originFilter'] == self.receiverId:
              sourceId = self.findRecvSessionByPort(state, relatedPath['originWriter'])
              if sourceId != None:
                self.lms.filterEvent(self.receiverId, 'removeSession', {'id': sourceId})

      self.updateGrid()

    
  def commuteChannel(self, channel):
    state = self.lms.getState()
    mixerCh = self.getChannels(state, self.videoMixerId)

    hasChnl = False
    for chnl in mixerCh:    
      if chnl['id'] == channel:
        hasChnl = True
        break

    if not hasChnl:
      raise Exception("The specified channel does not exist")

    for chnl in mixerCh:
      if chnl['id'] == channel:
        self.lms.filterEvent(self.videoMixerId, 'configChannel', 
                             {'id': channel, 
                               'width': 1, 'height': 1,
                               'x': 0, 'y': 0,
                               'layer': 0, 'enabled': True, 
                               'opacity': 1})
      else:
        self.lms.filterEvent(self.videoMixerId, 'configChannel', 
                             {'id': chnl['id'], 
                               'width': 1, 'height': 1,
                               'x': 0, 'y': 0,
                               'layer': 1, 'enabled': False,
                               'opacity': 1})

  def updateGrid(self):
    state = self.lms.getState()
    channels = self.getChannels(state, self.videoMixer2Id)
    mixCols = math.ceil(math.sqrt(len(channels)))

    layer = 0
    for channel in channels:
      self.lms.filterEvent(self.videoMixer2Id, 'configChannel', 
                           {'id': channel['id'], 
                             'width': 1 / mixCols, 'height': 1 / mixCols,
                             'x': (layer % mixCols) / mixCols, 
                             'y': (layer // mixCols) / mixCols,
                             'layer': layer, 'enabled': True, 
                             'opacity': 1})
      layer += 1

  def stopPipe(self):
    self.lms.stop()

  def setOutputFPS(self, fps, main = True):
    if fps > self.DEF_MAX_FPS:
      raise Exception("Maximum fps is {}, you entered {}.".format(*[self.DEF_MAX_FPS, fps]))

    state = self.lms.getState()

    if main:
      mixId = self.videoMixerId
      encId = self.videoEncoderId
    elif self.grid:
      mixId = self.videoMixer2Id
      encId = self.videoEncoder2Id
    else:
      raise Exception("Grid mode is not enabled")

    channels = self.getChannels(state, mixId)

    for channel in channels:
      path = self.getPathFromDst(state, mixId, channel['id'])
      if path == None:
        raise Exception("Path not found for channel {}".format(*[channel['id']]))
      for fId in path['filters']:
        if self.getFilterType(state, fId) == 'videoResampler':
          self.lms.filterEvent(fId, 'configure', {'fps': fps})

    self.lms.filterEvent(encId, 'configure', {'fps': fps})

  def setOutputResolution(self, width, height, main = True):
    state = self.lms.getState()

    if main:
      mixId = self.videoMixerId
    elif self.grid:
      mixId = self.videoMixer2Id
    else:
      raise Exception("There is no grid mode enabled")

    channels = self.getChannels(state, mixId)
    mixCols = math.ceil(math.sqrt(len(channels)))

    for channel in channels:
      path = self.getPathFromDst(state, mixId, channel['id'])
      if path == None:
        raise Exception("Path not found for channel {}".format(*[channel['id']]))
      for fId in path['filters']:
        if self.getFilterType(state, fId) == 'videoResampler':
          if main: 
            self.lms.filterEvent(fId, 'configure', {'width': width, 'height': height})
          else:
            self.lms.filterEvent(fId, 
                                 'configure', 
                                 {'width': width // mixCols,
                                  'height': height // mixCols})

    self.lms.filterEvent(mixId, 'configure', {'width': width, 'height': height})


  def setEncoderParams(self, bitrate, gop, lookahead, bFrames, threads, annexb, preset, main = True):
    if main:
      encId = self.videoEncoderId
    elif self.grid:
      encId = self.videoEncoder2Id 
    else:
      raise Exception("There is no grid mode enabled")

    self.lms.filterEvent(encId, 'configure', {'bitrate': bitrate, 'gop': gop, 
                                                'lookahead': lookahead, 'bframes': bFrames, 
                                                'threads': threads, 'annexb': annexb, 
                                                'preset': preset})

  def getEncoderParams(self, main = True):
    if main:
      encId = self.videoEncoderId
    elif self.grid:
      encId = self.videoEncoder2Id
    else:
      raise Exception("There is no grid mode enabled")

    state = self.lms.getState()
    
    for cFilter in state['filters']:
      if cFilter['id'] == encId:
        return cFilter

    return None

  def getSharedMemoryId(self):
    state = self.lms.getState()
    
    for cFilter in state['filters']:
      if cFilter['id'] == self.sharedMemoryId:
        return cFilter['memoryId']

