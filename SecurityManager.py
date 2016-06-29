import time
import math

from . import LMSManager

class SecurityManager:
  lms = None
  DEF_FPS = 25
  DEF_WIDTH = 1280
  DEF_HEIGHT = 720
  DEF_LOOKAHEAD = 0
  
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
    self.outputPathId = 1
    self.gridPathId = 2
    self.mainOutputStreamId = 1
    self.gridOutputStreamId = 2
    
  def startPipe(self):
    try:
      self.lms.createFilter(self.receiverId, 'receiver')
      self.lms.createFilter(self.transmitterId, 'transmitter')
      self.lms.createFilter(self.videoEncoderId, 'videoEncoder')
      self.lms.createFilter(self.videoMixerId, 'videoMixer')
      self.lms.createFilter(self.videoResamplerId, 'videoResampler')
      self.lms.createFilter(self.videoEncoder2Id, 'videoEncoder')
      self.lms.createFilter(self.videoMixer2Id, 'videoMixer')
      self.lms.createFilter(self.videoResampler2Id, 'videoResampler')
    except:
      self.lms.stop()
      raise Exception("Failed createing filters. Pipe cleared")

    self.lms.filterEvent(self.videoResamplerId, 'configure', {'pixelFormat': 2})
    self.lms.filterEvent(self.videoResampler2Id, 'configure', {'pixelFormat': 2})

    self.lms.filterEvent(self.videoMixerId, 
                         'configure', 
                         {'fps': self.DEF_FPS, 
                           'width': self.DEF_WIDTH,
                           'height': self.DEF_HEIGHT})

    self.lms.filterEvent(self.videoMixer2Id, 
                         'configure', 
                         {'fps': self.DEF_FPS, 
                           'width': self.DEF_WIDTH,
                           'height': self.DEF_HEIGHT})

    self.lms.filterEvent(self.videoEncoderId, 'configure', {'fps': self.DEF_FPS, 'lookahead': self.DEF_LOOKAHEAD})
    self.lms.filterEvent(self.videoEncoder2Id, 'configure', {'fps': self.DEF_FPS, 'lookahead': self.DEF_LOOKAHEAD})

    try:
      self.lms.createPath(self.outputPathId, 
                     self.videoMixerId, 
                     self.transmitterId, 
                     -1, self.mainOutputStreamId, 
                     [self.videoResamplerId, self.videoEncoderId])

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
                            'txFormat': 'mpegts', 
                            'readers': [self.mainOutputStreamId]})

    self.lms.filterEvent(self.transmitterId, 
                         'addRTSPConnection', 
                         {'id': self.gridOutputStreamId, 
                            'name': 'grid', 
                            'txFormat': 'mpegts', 
                            'readers': [self.gridOutputStreamId]})

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

  def getFilterType(self, state, fId):
    fType = None
    for cFilter in state['filters']:
      if cFilter['id'] == fId:
        fType = cFilter['type']
        break

    return fType

  def connectInputSource(self, state, inputFilterId, inputWriterId):
    decId = self.getMaxFilterId(state) + 1
    resId = decId + 1
    res2Id = resId + 1

    srcPathId = self.getMaxPathId(state) + 1
    mainPathId = srcPathId + 1
    gridPathId = mainPathId + 1

    outputReaderId = self.getMaxVideoChannel(state, self.videoMixerId) + 1

    try: 
      self.lms.createFilter(decId, "videoDecoder")
      self.lms.createFilter(resId, "videoResampler") 
      self.lms.createFilter(res2Id, "videoResampler")
    except: 
      raise Exception("Failed creating filters")

    size = self.getVideoMixerSize(state, self.videoMixerId)
    if size == None:
      raise Exception("Could not load main videoMixer size!")

    self.lms.filterEvent(resId, 'configure', {'fps': self.DEF_FPS, 
                                              'pixelFormat': 0,
                                              'width': size[0],
                                              'height': size[1]})

    size = self.getVideoMixerSize(state, self.videoMixer2Id)
    if size == None:
      raise Exception("Could not load grid videoMixer size!") 

    channels = self.getChannels(state, self.videoMixer2Id)
    mixCols = math.ceil(math.sqrt(len(channels) + 1))

    self.lms.filterEvent(res2Id, 'configure', {'fps': self.DEF_FPS, 
                                              'pixelFormat': 0,
                                              'width': size[0] // mixCols,
                                              'height': size[1] // mixCols})

    self.lms.createPath(srcPathId, 
                        inputFilterId,
                        decId,
                        inputWriterId, -1, [])

    self.lms.createPath(mainPathId, 
                        decId,
                        self.videoMixerId,
                        -1, outputReaderId,
                        [resId])

    self.lms.createPath(gridPathId, 
                        decId,
                        self.videoMixer2Id,
                        -1, -1,
                        [res2Id])

    return outputReaderId

  def getState():
    return self.lms.getState()

  def addRTSPSource(self, uri, sourceId):
    self.lms.filterEvent(self.receiverId, 'addSession', {'id': sourceId, 'uri': uri, 'progName': ''})

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

    chnl = self.connectInputSource(state, self.receiverId, port)

    self.commuteChannel(chnl)
    self.updateGrid() 

    return chnl
    
  def commuteChannel(self, channel):
    state = self.lms.getState()
    mixerCh = self.getChannels(state, self.videoMixerId)

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

  def setOutputFPS(self, fps, main):
    state = self.lms.getState()

    if main:
      mixId = self.videoMixerId
      encId = self.videoEncoderId
    else:
      mixId = self.videoMixer2Id
      encId = self.videoEncoder2Id

    channels = self.getChannels(state, mixId)

    for channel in channels:
      path = self.getPathFromDst(state, mixId, channel['id'])
      if path == None:
        raise Exception("Path not found for channel {}".format(*[channel['id']]))
      for fId in path['filters']:
        if self.getFilterType(state, fId) == 'videoResampler':
          self.lms.filterEvent(fId, 'configure', {'fps': fps})

    self.lms.filterEvent(mixId, 'configure', {'fps': fps})
    self.lms.filterEvent(encId, 'configure', {'fps': fps})

  def setOutputResolution(self, width, height, main):
    state = self.lms.getState()

    if main:
      mixId = self.videoMixerId
    else:
      mixId = self.videoMixer2Id

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



