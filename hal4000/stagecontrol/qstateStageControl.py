#!/usr/bin/python
#
## @file
#
# Stage control for qstate
#
# Hazen 02/14
#

from PyQt4 import QtCore

# stage.
import ludl.ludl as ludl

# stage control thread
import stagecontrol.stageThread as stageThread

# stage control dialog.
import stagecontrol.stageControl as stageControl

#
# QThread for communication with the Ludl stage for XY.
#
# This is necessary for position updates as otherwise
# the periodic communication with the Prior stage
# will cause the whole UI to behave a bit jerkily.
#
class QLudlThread(QtCore.QThread):
    def __init__(self, stage, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.stage = stage
        self.stage_position = [0.0, 0.0, 0.0]
        self.running = self.stage.getStatus()
        self.mutex = QtCore.QMutex()

    def getStatus(self):
        return self.running

    def goAbsolute(self, x, y):
        self.mutex.lock()
        self.stage.goAbsolute(x, y)
        self.stage_position = self.stage.position()
        self.mutex.unlock()

    def goRelative(self, dx, dy):
        self.mutex.lock()
        self.stage.goRelative(dx, dy)
        self.stage_position = self.stage.position()
        self.mutex.unlock()
        
    def lockout(self, flag):
        self.mutex.lock()
        self.stage.joystickOnOff(not flag)
        self.mutex.unlock()

    def position(self):
        self.mutex.lock()
        stage_position = self.stage_position
        self.mutex.unlock()
        return stage_position

    def run(self):
        while self.running:
            self.mutex.lock()
            self.stage_position = self.stage.position()
            self.mutex.unlock()
            self.msleep(500)

    def setVelocity(self, vx, vy):
        self.mutex.lock()
        self.stage.setVelocity(vx, vy)
        self.mutex.unlock()

    def shutDown(self):
        self.running = 0
        self.wait()
        self.stage.shutDown()

    def zero(self):
        self.mutex.lock()
        self.stage.zero()
        self.stage_position = self.stage.position()
        self.mutex.unlock()

#
# Stage control dialog specialized for qstate
# with marzhauser motorized stage.
#
class AStageControl(stageControl.StageControl):
    def __init__(self, hardware, parameters, parent = None):
        self.stage = QLudlThread(ludl.Ludl("COM1"))
        self.stage.start(QtCore.QThread.NormalPriority)
        stageControl.StageControl.__init__(self, 
                                           parameters,
                                           parent)

#
# The MIT License
#
# Copyright (c) 2014 Zhuang Lab, Harvard University
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
