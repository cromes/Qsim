from common.lib.clients.qtui.QCustomSpinBox import QCustomSpinBox
from twisted.internet.defer import inlineCallbacks
from PyQt4 import QtGui
from PyQt4.Qt import QPushButton
from config.dac_8718_config import dac_8718_config

import numpy as np


class dacclient(QtGui.QWidget):

    def __init__(self, reactor, parent=None):
        """initializes the GUI creates the reactor
            and empty dictionary for channel widgets to
            be stored for iteration.
        """

        super(dacclient, self).__init__()
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.reactor = reactor
        self.d = {}
        self.e = {}
        self.topelectrodes = {'DAC 0': 0, 'DAC 1': 1, 'DAC 2': 2, 'DAC 3': 3}
        self.bottomelectrodes = {'DAC 4': 4,  'DAC 5': 5,  'DAC 6': 6, 'DAC 7': 7}
        self.xminuselectrodes = {'DAC 2': 2, 'DAC 6': 6}
        self.xpluselectrodes = {'DAC 0': 0, 'DAC 4': 4}
        self.yminuselectrodes = {'DAC 1': 1, 'DAC 5': 5}
        self.ypluselectrodes = {'DAC 3': 3, 'DAC 7': 7}
        self.connect()

    @inlineCallbacks
    def connect(self):
        """Creates an Asynchronous connectiontry:
    from config.arduino_dac_config import arduino_dac_config
except:
    from common.lib.config.arduino_dac_config import arduino_dac_config
        """
        from labrad.wrappers import connectAsync
        from labrad.units import WithUnit as U

        self.U = U
        self.cxn = yield connectAsync(name="dac8718 client")
        self.server = yield self.cxn.dac8718_server
        self.reg = yield self.cxn.registry

        try:
            yield self.reg.cd('settings')
            self.settings = yield self.reg.dir()
            self.settings = self.settings[1]
        except:
            self.settings = []

        self.config = dac_8718_config
        self.initializeGUI()

    @inlineCallbacks
    def initializeGUI(self):

        layout = QtGui.QGridLayout()

        qBox = QtGui.QGroupBox('DAC Channels')
        subLayout = QtGui.QGridLayout()
        qBox.setLayout(subLayout)
        layout.addWidget(qBox, 0, 0)
        self.multipole_step = 10
        self.currentvalues = {}

        self.Ex_label = QtGui.QLabel('E_x')
        self.Ey_label = QtGui.QLabel('E_y')
        self.Ez_label = QtGui.QLabel('E_z')

        for channel_key in self.config.channels:
            name = self.config.channels[channel_key].name
            chan_number = self.config.channels[channel_key].number

            widget = QCustomSpinBox(name, (0, 2**16 - 1))
            widget.title.setFixedWidth(120)
            label = QtGui.QLabel('0 V')
            if name in self.settings:
                value = yield self.reg.get(name)
                widget.spinLevel.setValue(value)
                self.currentvalues.update({name: value})
                self.setvalue(value, [name, chan_number])
            else:
                widget.spinLevel.setValue(0.0)
            widget.setStepSize(1)
            widget.spinLevel.setDecimals(0)
            widget.spinLevel.valueChanged.connect(lambda value=widget.spinLevel.value(),
                                                  ident=[name, chan_number]: self.setvalue(value, ident))
            self.d[chan_number] = widget
            self.e[chan_number] = label
            subLayout.addWidget(self.d[chan_number],  chan_number, 1)
            subLayout.addWidget(self.e[chan_number], chan_number, 2)

        self.exsqueezeupwidget = QPushButton('X Squeeze increase')
        self.exsqueezedownwidget = QPushButton('X Squeeze decrease')
        self.eysqueezeupwidget = QPushButton('Y Squeeze increase')
        self.eysqueezedownwidget = QPushButton('Y Squeeze decrease')

        self.ezupwidget = QPushButton('Ez increase')
        self.ezdownwidget = QPushButton('Ez decrease')
        self.exupwidget = QPushButton('Ex increase')
        self.exdownwidget = QPushButton('Ex decrease')
        self.eyupwidget = QPushButton('Ey increase')
        self.eydownwidget = QPushButton('Ey decrease')
        self.save_widget = QPushButton('Save current values to Registry')

        self.dipole_res = QCustomSpinBox('Dipole Res', (0, 1000))
        self.dipole_res.spinLevel.setValue(10)
        self.dipole_res.setStepSize(1)
        self.dipole_res.spinLevel.setDecimals(0)

        self.exsqueezeupwidget.clicked.connect(self.ex_squeeze_up)
        self.eysqueezeupwidget.clicked.connect(self.ey_squeeze_up)

        self.exsqueezedownwidget.clicked.connect(self.ex_squeeze_down)
        self.eysqueezedownwidget.clicked.connect(self.ey_squeeze_down)

        self.ezupwidget.clicked.connect(self.ezup)
        self.ezdownwidget.clicked.connect(self.ezdown)
        self.exupwidget.clicked.connect(self.exup)
        self.exdownwidget.clicked.connect(self.exdown)
        self.eyupwidget.clicked.connect(self.eyup)
        self.eydownwidget.clicked.connect(self.eydown)
        self.dipole_res.spinLevel.valueChanged.connect(self.update_dipole_res)
        self.save_widget.clicked.connect(self.save_to_registry)

        subLayout.addWidget(self.ezupwidget,   0, 5)
        subLayout.addWidget(self.ezdownwidget, 1, 5)
        subLayout.addWidget(self.exupwidget,   3, 6)
        subLayout.addWidget(self.exdownwidget, 3, 3)
        subLayout.addWidget(self.eyupwidget,   2, 5)
        subLayout.addWidget(self.eydownwidget, 4, 5)
        subLayout.addWidget(self.dipole_res,   3, 5)
        subLayout.addWidget(self.save_widget,  5, 5)
        subLayout.addWidget(self.Ex_label,     6, 5)
        subLayout.addWidget(self.Ey_label,     7, 5)
        subLayout.addWidget(self.Ez_label,     8, 5)

        subLayout.addWidget(self.exsqueezeupwidget,   6, 6)
        subLayout.addWidget(self.exsqueezedownwidget, 6, 7)
        subLayout.addWidget(self.eysqueezeupwidget,   7, 6)
        subLayout.addWidget(self.eysqueezedownwidget, 7, 7)

        self.setLayout(layout)

    @inlineCallbacks

    def ezup(self, isheld):
        for name, dacchan in self.topelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

        for name, dacchan in self.bottomelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)

    @inlineCallbacks
    def ezdown(self, isheld):
        for name, dacchan in self.bottomelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

        for name, dacchan in self.topelectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)

    @inlineCallbacks
    def exup(self, isheld):
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)
        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

    @inlineCallbacks
    def exdown(self, isheld):
        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

    @inlineCallbacks
    def eyup(self, isheld):
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)
        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

    @inlineCallbacks
    def eydown(self, isheld):
        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

    @inlineCallbacks
    def ey_squeeze_up(self, isheld):
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)
        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

    @inlineCallbacks
    def ey_squeeze_down(self, isheld):
        for name, dacchan in self.ypluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)
        for name, dacchan in self.yminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)

    @inlineCallbacks
    def ex_squeeze_up(self, isheld):
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)
        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue >= 2**16 - 1:
                break
            yield self.setvalue(currentvalue + self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue + self.multipole_step)

    @inlineCallbacks
    def ex_squeeze_down(self, isheld):
        for name, dacchan in self.xpluselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)
        for name, dacchan in self.xminuselectrodes.iteritems():
            currentvalue = self.currentvalues[name]
            if currentvalue <= 0:
                break
            yield self.setvalue(currentvalue - self.multipole_step, [name, dacchan])
            self.d[dacchan].spinLevel.setValue(currentvalue - self.multipole_step)



    @inlineCallbacks
    def setvalue(self, value, ident):
        name = ident[0]
        chan = ident[1]
        value = int(value)
        yield self.server.dacoutput(chan, value)
        voltage = (2.2888e-4*value - 7.5)
        self.e[chan].setText(str(voltage))
        self.currentvalues[name] = value
        self.setdipoles()

    def bit_to_volt(self, bit):
        voltage = (2.2888e-4*bit - 7.5)
        return voltage

    def setdipoles(self):

        xpluskeys = self.xpluselectrodes.keys()
        xminuskeys = self.xminuselectrodes.keys()
        xplustop = self.bit_to_volt(self.currentvalues[xpluskeys[0]])
        xplusbottom = self.bit_to_volt(self.currentvalues[xpluskeys[1]])
        xminustop = self.bit_to_volt(self.currentvalues[xminuskeys[0]])
        xminusbottom = self.bit_to_volt(self.currentvalues[xminuskeys[1]])

        ypluskeys = self.ypluselectrodes.keys()
        yminuskeys = self.yminuselectrodes.keys()
        yplustop = self.bit_to_volt(self.currentvalues[ypluskeys[0]])
        yplusbottom = self.bit_to_volt(self.currentvalues[ypluskeys[1]])
        yminustop = self.bit_to_volt(self.currentvalues[yminuskeys[0]])
        yminusbottom = self.bit_to_volt(self.currentvalues[yminuskeys[1]])

        zpluskeys = self.topelectrodes.keys()
        zminuskeys = self.bottomelectrodes.keys()
        zplustop = self.bit_to_volt(self.currentvalues[zpluskeys[0]])
        zplusbottom = self.bit_to_volt(self.currentvalues[zpluskeys[1]])
        zminustop = self.bit_to_volt(self.currentvalues[zminuskeys[0]])
        zminusbottom = self.bit_to_volt(self.currentvalues[zminuskeys[1]])

        xplus = np.mean([xplustop, xplusbottom])
        xminus = np.mean([xminustop, xminusbottom])
        xdipole = (xplus - xminus)

        yplus = np.mean([yplustop, yplusbottom])
        yminus = np.mean([yminustop, yminusbottom])
        ydipole = (yplus - yminus)

        zplus = np.mean([zplustop, zplusbottom])
        zminus = np.mean([zminustop, zminusbottom])
        zdipole = (zplus - zminus)

        self.Ex_label.setText('Ex = ' + str(xdipole))
        self.Ey_label.setText('Ey = ' + str(ydipole))
        self.Ez_label.setText('Ez = ' + str(zdipole))


    def update_dipole_res(self, value):
        self.multipole_step = value

    def save_to_registry(self):
        for chan in self.currentvalues:
            self.reg.set(chan, self.currentvalues[chan])

    def closeEvent(self, x):
        print 'Saving DAC values to regisry...'
        self.save_to_registry()
        print 'Saved.'
        self.reactor.stop()


if __name__ == "__main__":
    a = QtGui.QApplication([])
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    dacWidget = dacclient(reactor)
    dacWidget.show()
    reactor.run()  # @UndefinedVariable
