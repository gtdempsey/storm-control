#!/usr/bin/python
#
## @file
#
# Illumination control specialized for qstate
#
# Hazen 02/14
#

from PyQt4 import QtCore

import nationalInstruments.nicontrol as nicontrol

import illumination.channelWidgets as channelWidgets
import illumination.commandQueues as commandQueues
import illumination.illuminationControl as illuminationControl
import illumination.shutterControl as shutterControl

import coherent.cube405 as cube405

#
# Illumination power control specialized for qstate.
#
class qstateQIlluminationControlWidget(illuminationControl.QIlluminationControlWidget):
    def __init__(self, settings_file_name, parameters, parent = None):
        # setup the AOTF communication thread
        self.aotf_queue = commandQueues.QGHAOTFThread()
        self.aotf_queue.start(QtCore.QThread.NormalPriority)
        self.aotf_queue.analogModulationOn()

        # setup for NI communication with mechanical shutters (digital, unsynced)
        self.shutter_queue = commandQueues.QNiDigitalComm()

        # turn on laser
        nicontrol.setDigitalLine("PCIe-6343", 6, True)

        illuminationControl.QIlluminationControlWidget.__init__(self, settings_file_name, parameters, parent)

        # set frequencies for channels
        for channel in self.channels:
            channel.setFrequency()

    def autoControl(self, channels):
        for channel in self.channels:
            channel.setFilmMode(1)

    def manualControl(self):
        for channel in self.channels:
            channel.setFilmMode(0)

    def newParameters(self, parameters):
        illuminationControl.QIlluminationControlWidget.newParameters(self, parameters)

        # Layout the widget
        dx = 50
        width = self.number_channels * dx

        # The height is based on how many buttons there are per channel,
        # so first we figure out the number of buttons per channel.
        max_buttons = 0
        for i in range(self.number_channels):
            n_buttons = len(parameters.power_buttons[i])
            if n_buttons > max_buttons:
                max_buttons = n_buttons
        height = 204 + max_buttons * 22

        # Set the size based on the number of channels and buttons
        self.resize(width, height)
        self.setMinimumSize(QtCore.QSize(width, height))
        self.setMaximumSize(QtCore.QSize(width, height))

        # Create the individual channels
        x = 0
        for i in range(self.number_channels):
            n = self.settings[i].channel
            if hasattr(self.settings[i], 'use_aotf'):
                channel = channelWidgets.QAOTFChannelWShutter(self,
                                                              self.settings[i],
                                                              parameters.default_power[n],
                                                              parameters.on_off_state[n],
                                                              parameters.power_buttons[n],
                                                              x,
                                                              dx,
                                                              height)
                channel.setCmdQueue(self.aotf_queue)
                channel.setShutterQueue(self.shutter_queue)
                channel.fskOnOff(1)
                self.channels.append(channel)
            elif hasattr(self.settings[i], 'basic_shutter'):
                channel = channelWidgets.QBasicChannel(self,
                                                       self.settings[i],
                                                       parameters.on_off_state[n],
                                                       x,
                                                       dx,
                                                       height)
                channel.setShutterQueue(self.shutter_queue)
                self.channels.append(channel)
            x += dx

        # Update the channels to reflect there current ui settings.
        for channel in self.channels:
            channel.uiUpdate()
                            
        # Save access to the previous parameters file so that
        # we can save the settings when the parameters are changed.
        self.last_parameters = parameters

    def shutDown(self):
        illuminationControl.QIlluminationControlWidget.shutDown(self)
        self.aotf_queue.stopThread()
        self.aotf_queue.wait()

        # Turn lasers off.
        nicontrol.setDigitalLine("PCIe-6343", 6, False)



#
# qstate shutter control.
#
#
# These are driven by the analog out lines of a
# National Instruments PCI-6343 card.
#
class qstateShutterControl(shutterControl.ShutterControl):
    def __init__(self, powerToVoltage, parent):
        shutterControl.ShutterControl.__init__(self, powerToVoltage, parent)
        self.oversampling_default = 1
        self.number_channels = 2

        self.board = "PCIe-6343"
        self.ct_task = False
        self.do_task = False
        self.wv_task = False

        self.defaultAOTFLines()

    def cleanup(self):
        if self.ct_task:
            self.ct_task.clearTask()
            self.do_task.clearTask()
            self.wv_task.clearTask()
            self.ct_task = 0
            self.do_task = 0
            self.wv_task = 0

    def defaultAOTFLines(self):
        nicontrol.setAnalogLine(self.board, 3, self.powerToVoltage(1, 1.0))
        nicontrol.setDigitalLine(self.board, 12, True)

    def prepare(self):
        nicontrol.setAnalogLine(self.board, 3, 0.0)

    def setup(self):
        assert self.ct_task == 0, "Attempt to call setup without first calling cleanup."
        #
        # the counter runs slightly faster than the camera so that it is ready
        # to catch the next camera "fire" immediately after the end of the cycle.
        #
        frequency = (1.001/self.kinetic_value) * float(self.oversampling)

        print self.waveforms

        # set up the analog channels
        self.wv_task = nicontrol.WaveformOutput(self.board, 0)
        self.wv_task.addChannel(3)

        # set up the digital channels
        self.do_task = nicontrol.DigitalWaveformOutput(self.board, 7)
        self.do_task.addChannel(self.board, 12)

        # set up the waveform
        self.wv_task.setWaveform(self.waveforms, frequency, clock = "PFI12")
        self.do_task.setWaveform(self.waveforms, frequency, clock = "PFI12")

        # set up the counter
        self.ct_task = nicontrol.CounterOutput(self.board, 0, frequency, 0.5)
        self.ct_task.setCounter(self.waveform_len)
        self.ct_task.setTrigger(1)

    def startFilm(self):
        self.wv_task.startTask()
        self.do_task.startTask()
        self.ct_task.startTask()

    def stopFilm(self):
        # stop the tasks
        if self.ct_task:
            self.ct_task.stopTask()
            self.do_task.stopTask()
            self.wv_task.stopTask()
            self.ct_task.clearTask()
            self.do_task.clearTask()
            self.wv_task.clearTask()
            self.ct_task = 0
            self.do_task = 0
            self.wv_task = 0

        # reset all the analog signals.
        self.defaultAOTFLines()
        


#
# Illumination power control dialog box specialized for STORM3.
#
class AIlluminationControl(illuminationControl.IlluminationControl):
    def __init__(self, hardware, parameters, parent = None):
        illuminationControl.IlluminationControl.__init__(self, parameters, parent)
        self.power_control = qstateQIlluminationControlWidget("illumination/" + hardware.settings_xml,
                                                              parameters,
                                                              parent = self.ui.laserBox)
        self.shutter_control = qstateShutterControl(self.power_control.powerToVoltage,
                                                    self.ui.laserBox)
        self.updateSize()

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
