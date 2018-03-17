'''
(*)~----------------------------------------------------------------------------------
 Pupil - eye tracking platform
 Copyright (C) 2012-2016  Pupil Labs

 Distributed under the terms of the GNU Lesser General Public License (LGPL v3.0).
 License details are in the file license.txt, distributed as part of this software.
----------------------------------------------------------------------------------~(*)
'''
#Modded version, based on fake_backend. Original by Shahram Jalaliniya, updated and modified by Anton Gustafsson.
from video_capture.base_backend import Base_Source, Base_Manager, Playback_Source

import cv2
import uvc
import numpy as np
from time import time,sleep
from pyglui import ui
import threading
from camera_models import Dummy_Camera
from threading import Thread

#logging
import logging
logger = logging.getLogger(__name__)

class Frame(object):
    """docstring of Frame"""
    def __init__(self, timestamp,img,index):
        self.timestamp = timestamp
        self._img = img
        self.bgr = img
        self.height,self.width,_ = img.shape
        self._gray = None
        self.index = index
        #indicate that the frame does not have a native yuv or jpeg buffer
        self.yuv_buffer = None
        self.jpeg_buffer = None

    @property
    def img(self):
        return self._img

    @property
    def gray(self):
        if self._gray is None:
            self._gray = cv2.cvtColor(self.img,cv2.COLOR_BGR2GRAY)
        return self._gray

    @gray.setter
    def gray(self, value):
        raise Exception('Read only.')

class None_UVC_Source(Playback_Source,Base_Source):
    def __init__(self, g_pool, source_path=None, frame_size=None,
                 frame_rate=None, name='webcam', *args, **kwargs):
        super().__init__(g_pool, *args, **kwargs)
        self._name = name
        self.fps = 30
        self.presentation_time = time()
        self.make_img((640,480))
        self.frame_count = 0
          
    @property
    def name(self):
        return self._name

    def cleanup(self):
        self.info_text = None
        self.preferred_source = None

    def gl_display(self):
        super().gl_display()
        if hasattr(self,'glfont'):
            from glfw import glfwGetFramebufferSize,glfwGetCurrentContext
            self.window_size = glfwGetFramebufferSize(glfwGetCurrentContext())
            self.glfont.set_color_float((0.,0.,0.,1.))
            self.glfont.set_size(int(self.window_size[0]/30.))
            self.glfont.set_blur(5.)
            self.glfont.draw_limited_text(self.window_size[0]/2.,self.window_size[1]/2.,self.info_text,self.window_size[0]*0.8)
            self.glfont.set_blur(0.96)
            self.glfont.set_color_float((1.,1.,1.,1.0))
            self.glfont.draw_limited_text(self.window_size[0]/2.,self.window_size[1]/2.,self.info_text,self.window_size[0]*0.8)

    def make_img(self,size):
        self._img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        self._img[:, :, 0] += np.linspace(91, 157, self.frame_size[0], dtype=np.uint8)
        self._img[:, :, 1] += np.linspace(100, 1, self.frame_size[0], dtype=np.uint8)
        self._img[:, :, 2] += np.linspace(100, 112, self.frame_size[0], dtype=np.uint8)
        self._intrinsics = Dummy_Camera(size, self.name)

    @property
    def img(self):
        return self._img

    def recent_events(self, events):
        frame = self.get_frame()
        events['frame'] = frame
        self._recent_frame = frame

    def get_frame(self):
        now =  time()
        spent = now - self.presentation_time
        wait = max(0,1./self.fps - spent) 
        sleep(wait)
        self.presentation_time = time()
        frame_count = self.frame_count
        self.frame_count +=1
        timestamp = self.g_pool.get_timestamp()
        return Frame(timestamp,self.g_pool.capture._img.copy(),frame_count)
        
    @property
    def settings(self):
        return {'frame_size': self.frame_size, 'frame_rate': self.frame_rate}

    @settings.setter
    def settings(self,settings):
        self.frame_size = settings.get('frame_size', self.frame_size)
        self.frame_rate = settings.get('frame_rate', self.frame_rate )

    @property
    def frame_size(self):
        return self.img.shape[1],self.img.shape[0]

    @frame_size.setter
    def frame_size(self,new_size):
        sizes = [ abs(r[0]-new_size[0]) for r in self.frame_sizes ]
        best_size_idx = sizes.index(min(sizes))
        size = self.frame_sizes[best_size_idx]
        if size != new_size:
            logger.warning("%s resolution capture mode not available. Selected %s."%(new_size,size))
        self.make_img(size)

    @property
    def frame_rates(self):
        return (30,30)

    @property
    def frame_sizes(self):
        return ((640,480),(1280,720),(1920,1080))

    @property
    def frame_rate(self):
        return self.fps

    @frame_rate.setter
    def frame_rate(self,new_rate):
        rates = [ abs(r-new_rate) for r in self.frame_rates ]
        best_rate_idx = rates.index(min(rates))
        rate = self.frame_rates[best_rate_idx]
        if rate != new_rate:
            logger.warning("%sfps capture mode not available at (%s) on 'Fake Source'. Selected %sfps. "%(new_rate,self.frame_size,rate))
        self.fps = rate

    @property
    def jpeg_support(self):
        return False

    @property
    def img(self):
        return self._img

class None_UVC_Manager(Base_Manager):
    gui_name = 'None UVC'

    def __init__(self, g_pool):
        super().__init__(g_pool)
        self.devices = uvc.Device_List()

    def init_ui(self):
        self.add_menu()
        from pyglui import ui
        ui_elements = []
        ui_elements.append(ui.Info_Text('With the None UVC manager you can select regular webcams as your source. Beaware that the list could show more devices than you have plugged in and thus selecting a "invalid" device will result in a grey image. As this code uses a separate thread a complete reset of the application is needed if you want to change sources'))

        def dev_selection_list():
            default = (None, 'Select to activate')
            self.devices.update()
            dev_pairs = [default] + [(str(index), str(index)) for index,d in enumerate(self.devices)]
            return zip(*dev_pairs)

        def activate(source_uid):
            msg ='Button pressed.'
            print (msg)
            print (source_uid)
            if(source_uid != None):
                self.notify_all({'subject': 'recording.should_stop'})
                settings = {}
                settings['timed_playback'] = True
                settings['frame_rate'] = self.g_pool.capture.frame_rate
                settings['frame_size'] = self.g_pool.capture.frame_size
                settings['name'] = 'None_UVC_Source'
                if self.g_pool.process == 'world':
                    self.notify_all({'subject':'start_plugin',"name":"None_UVC_Source",'args':settings})
                else:
                     self.notify_all({'subject':'start_eye_capture','target':self.g_pool.process, "name":"None_UVC_Source",'args':settings})

                threading.Thread(target=self._activate_source,args=(int(source_uid),)).start()
       
        ui_elements.append(ui.Selector(
            'selected_source',
            selection_getter=dev_selection_list,
            getter=lambda: None,
            setter=activate,
            label='Sources:'
        ))

        self.menu.extend(ui_elements)

    #A thread polling for camera images.
    def _activate_source(self,cam):
        print ('Thread created for saving camera images!')
        capture = cv2.VideoCapture(cam)
        ret, image = capture.read()
        while ret:
            ret, image = capture.read()
            self.g_pool.capture._img = cv2.resize(image,(640,480),interpolation=cv2.INTER_LANCZOS4)
            

    def deinit_ui(self):
        self.remove_menu()

    def cleanup(self):
        self.devices.cleanup()
        self.devices = None

    def recent_events(self,events):
        pass