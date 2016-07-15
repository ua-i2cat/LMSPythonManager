"""
MultimediaManager.py  - This is a controller for a remote LMS instance
                        for a multimedia scenario
 
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

from . import LMSManager

class MultimediaManager:
  lms =  None
  DEF_SEG_DURATION =  4
  DEF_LOOKAHEAD = 25
  DEF_FPS =  25
  DEF_DASH_PROFILES = [{'width': 1920, 
                        'height': 1080, 
                        'bitrate': 6000000, 
                        'fps': 25},
                        {'width': 1360, 
                        'height': 768, 
                        'bitrate': 4000000, 
                        'fps': 25},
                        {'width': 1280, 
                        'height': 720, 
                        'bitrate': 3000000, 
                        'fps': 25},
                        {'width': 960, 
                        'height': 540, 
                        'bitrate': 2000000, 
                        'fps': 25},
                        {'width': 640, 
                        'height': 360, 
                        'bitrate': 1000000, 
                        'fps': 25},
                        {'width': 640, 
                        'height': 360, 
                        'bitrate': 500000, 
                        'fps': 12}]

  def __init__(self, host, port):
    """MultimediaManager constructor

    It creates a new istance of the MultimediaManager. 

    Args:
      host: The host in which the LiveMediaStreamer is running.
      port: The port in which the LiveMediaStreamer is listening. 
    """
    self.lms = LMSManager.LMSManager(host, port)
    self.receiverId = 1
    self.vDecoderId = 2
    self.aDecoderId = 3
    self.rtmpDemuxId = 4
    self.sharedMemoryId = 5
    self.dasherId = 6
   
  def startPipe(self):
    """Starts a pipe with the appropriate outputs.

    It creates all the filters and paths which do not depend on
    the input sources. Note this is method is coupled with a concrete 
    scenario configuration (dasher in this case).
    """
    try:
      self.lms.createFilter(self.dasherId, 'dasher')
    except:
      self.lms.stop()
      raise Exception("Failed creating filters. Pipe cleared")

  def configureDasher(self, folder, baseName, segDurInSec, maxSeg, minBuffTime):
    self.lms.filterEvent(self.dasherId, 'configure', 
                          {'folder': folder,
                           'baseName': baseName,
                           'segDurInSec': segDurInSec,  
                           'maxSeg': maxSeg,
                           'minBuffTime': minBuffTime})

  def addRTSPSource(self, uri, keepAlive = True, profiles = [0, 2, 4]):
    """Sends required events to add a new RTSP stream as input.

    This method initiates an RTSP negotionation, if the negotiation does not conclude
    in less than ten seconds, the method fails. Once the negotiation is completed the
    method registers the new input and creates all required filters (i.e. decoders) and 
    paths to start processing this input.

    Args: 
      uri: The RTSP uri of the input source (i.e. the URL of an IP camera)
      keepAlive: A boolean to enable/disable the keep alive messages form the client
      to the server. Some RTSP server require periodic GET_PAMETERS messages in order
      to keep the session alive. Enbled by default. Optional parameter.  
      profiles: list of the profiles to be used, passed as a list of indexes of
      indexes of DEF_DASH_PROFILES constant list. Optional parameters. Default 
      value is [0, 2, 4]. 
      

    Returns:
      The channel assigned to the source. This channel ID will be needed for later management 
      of this source input.    

    Raises:
      Exception: In case of failure raises an Exception. 
    """
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
    except AttributeError:
      # It seams old versions of urllib3 do not have url submodule
      sourceUrl = urllib3.util.parse_url(uri) 
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

    chnl = self.connectInputSource(state, self.receiverId, port, profiles)
      
    return chnl

  def connectInputSource(self, state, inputFilterId, inputWriterId, profiles):
    decId = self.getMaxFilterId(state) + 1
    shmId = decId + 1
    
    try: 
      self.lms.createFilter(decId, "videoDecoder")
      self.lms.createFilter(shmId, "sharedMemory")
    except
      self.lms.removeFilter(decId)
      self.lms.removeFilter(shmId)
      raise Exception("Failed creating filters")

    srcPathId = self.getMaxPathId(state) + 1
    
    try:
      self.createPath(srcPathId, inputFilterId, shmId, 
                      inputWriterId, -1, [decId])
    except:
      self.lms.removeFilter(decId)
      self.lms.removeFilter(shmId)
      raise Exception("Failed creating path")

    for profile in set(profiles):
      if profile >= len(self.DEF_DASH_PROFILES):
        continue
      try:
        self.addRepresentation(self.lms.getState(), shmId, 
                               self.DEF_DASH_PROFILES[profile])
      except:
        logging.error('Failed creating profile {}'.format(*[profile]))

  def addRepresentation(self, state, inputFilterId, profile):
    resId = self.getMaxFilterId(state) + 1 
    encId = resId + 1

    try: 
      self.lms.createFilter(resId, "videoResampler")
      self.lms.createFilter(encId, "videoEncoder")
    except
      self.lms.removeFilter(resId)
      self.lms.removeFilter(encId)
      raise Exception("Failed creating filters")
      
    self.lms.filterEvent(resId, 'configure', 
                          {'pixelFormat': 2, 
                          'width': profile['width'],
                          'height': profile['height']})

    self.lms.filterEvent(encId, 'configure', 
                         {'fps': profile['fps'], 
                         'bitrate': profile['bitrate']
                         'gop': profile['fps']})

    srcPathId = self.getMaxPathId(state) + 1

    try:
      self.createPath(srcPathId, inputFilterId, self.dasherId, 
                      -1, -1, [resId, encId])

    except:
      self.lms.removeFilter(resId)
      self.lms.removeFilter(encId)
      raise Exception("Failed creating path")
      
    #TODO send force intras to encoders

        

