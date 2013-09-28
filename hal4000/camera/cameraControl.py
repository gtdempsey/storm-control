#!/usr/bin/python
#
# Qt Thread for handling camera data capture and recording. 
# All communication with the camera should go through this 
# class (of which there should only be one instance). This
# is a generic class and should be specialized for control
# of particular camera types.
#
# Hazen 09/13
#

from PyQt4 import QtCore

# Debugging
import halLib.hdebug as hdebug

#
# Camera update thread. All camera control is done by this thread.
# Classes for controlling specific cameras should be subclasses
# of this class that implement at least the following methods:
#
# getAcquisitionTimings()
#    Returns the current acquisition timings as a triple:
#    [time, time, time]
#
# initCamera()
#    Initializes the camera.
#
# newParameters()
#    Setup the camera with the new acquisition parameters.
#
# run()
#    This is the main thread loop that gets data from the
#    camera and sends signals to the control program that
#    data is available, etc.
#
# See noneCameraControl.py or andorCameraControl.py for examples.
#
#
# This class generates two kinds of Qt signals:
#
# 1. reachedMaxFrames() when the camera has acquired the
#    number of frames it was told to acquire by the
#    parameters.frames.
#
# 2. newData() when new data has been received from the camera.
#    Data is supplied as a list of frame objects as part of
#    the signal.
#
class CameraControl(QtCore.QThread):
    reachedMaxFrames = QtCore.pyqtSignal()
    newData = QtCore.pyqtSignal(object, int)

    @hdebug.debug
    def __init__(self, parameters, parent = None):
        QtCore.QThread.__init__(self, parent)

        p = parameters

        # other class initializations
        self.acquire = IdleActive()
        self.daxfile = False
        self.filming = False
        self.frame_number = 0
        self.key = -1
        self.max_frames_sig = SingleShotSignal(self.reachedMaxFrames)
        self.mode = "run_till_abort"
        self.mutex = QtCore.QMutex()
        self.running = True
        self.shutter = False

        # camera initialization
        self.camera = False
        self.got_camera = False
        self.reversed_shutter = False

    def cameraInit(self):
        self.start(QtCore.QThread.NormalPriority)

    @hdebug.debug
    def closeShutter(self):
        self.shutter = False

    @hdebug.debug
    def getFilmSize(self):
        film_size = 0
        if self.daxfile:
            self.mutex.lock()
            film_size = self.daxfile.totalFilmSize()
            self.mutex.unlock()
        return film_size

    @hdebug.debug
    def getTemperature(self):
        return [50, "unstable"]

    @hdebug.debug
    def newFilmSettings(self, parameters, filming = False):
        self.mutex.lock()
        self.parameters = parameters
        p = parameters
        if filming:
            self.acq_mode = p.acq_mode
        else:
            self.acq_mode = "run_till_abort"
        self.acquired = 0
        self.filming = filming
        self.mutex.unlock()

    @hdebug.debug
    def openShutter(self):
        self.shutter = True

    @hdebug.debug
    def quit(self):
        self.stopThread()
        self.wait()

    @hdebug.debug
    def setEMCCDGain(self, gain):
        pass

    @hdebug.debug        
    def startCamera(self, key):
        self.mutex.lock()
        self.acquire.go()
        self.frame_number = 0
        self.key = key
        self.max_frames_sig.reset()
        self.mutex.unlock()

    @hdebug.debug
    def startFilm(self, daxfile):
        if daxfile:
            self.daxfile = daxfile
        self.newFilmSettings(self.parameters, filming = True)

    @hdebug.debug
    def stopCamera(self):
        self.mutex.lock()
        self.acquire.stop()
        self.mutex.unlock()

    @hdebug.debug
    def stopThread(self):
        self.running = False

    @hdebug.debug
    def stopFilm(self):
        self.newFilmSettings(self.parameters)
        self.daxfile = False

    @hdebug.debug
    def toggleShutter(self):
        if self.shutter:
            self.closeShutter()
            return False
        else:
            self.openShutter()
            return True

#
# A traffic light class.
#
# This class handles signaling between the thread run function and the
# rest of the thread. If "go" then the run method performs the
# requested operations. If "stop" then the run method acknowledges
# that it is idling.
#
class IdleActive():

    def __init__(self):
        self.idle = False
        self.run = False

    def amActive(self):
        return self.run

    def amIdle(self):
        return self.idle

    def go(self):
        self.idle = False
        self.run = True

    def idle(self):
        self.idle = True

    def stop(self):
        self.run = False

#
# Single shot signal class.
#
# This class creates a signal that needs to be reset each time it is emitted.
#
class SingleShotSignal():
 
    def __init__(self, pyqt_signal):
        self.emitted = False
        self.pyqt_signal = pyqt_signal

    def emit(self):
        if not self.emitted:
            self.pyqt_signal.emit()
            self.emitted = True

    def reset(self):
        self.emitted = False

#
# The MIT License
#
# Copyright (c) 2013 Zhuang Lab, Harvard University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

