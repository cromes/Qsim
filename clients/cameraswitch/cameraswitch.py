from common.lib.clients.qtui.switch import QCustomSwitchChannel
from twisted.internet.defer import inlineCallbacks
from common.lib.clients.connection import connection
from PyQt4 import QtGui


class cameraswitch(QtGui.QWidget):

    def __init__(self, reactor, cxn=None):
        super(cameraswitch, self).__init__()
        self.setSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        self.reactor = reactor
        self.cxn = cxn
        self.connect()

    @inlineCallbacks
    def connect(self):
        """Creates an Asynchronous connection to arduinottl and
        connects incoming signals to relavent functions

        """

        if self.cxn is None:
            self.cxn = connection(name="Camera Switch")
            yield self.cxn.connect()
        self.server = yield self.cxn.get_server('arduinottl')
        self.reg = yield self.cxn.get_server('registry')

        try:
            yield self.reg.cd('settings')
            self.settings = yield self.reg.dir()
            self.settings = self.settings[1]
        except:
            self.settings = []
        self.initializeGUI()

    @inlineCallbacks
    def initializeGUI(self):
        layout = QtGui.QGridLayout()
        widget = QCustomSwitchChannel('Camera/PMT Toggle', ('PMT', 'Camera'))
        RFwidget = QCustomSwitchChannel('RF Drive Switch', ('RF On', 'RF Off'))
        if 'cameraswitch' in self.settings:
            value = yield self.reg.get('cameraswitch')
            value = bool(value)
            widget.TTLswitch.setChecked(value)
        else:
            widget.TTLswitch.setChecked(False)

        if 'RFswitch' in self.settings:
            value = yield self.reg.get('RFswitch')
            value = bool(value)
            RFwidget.TTLswitch.setChecked(value)

        widget.TTLswitch.toggled.connect(self.toggle)
        RFwidget.TTLswitch.toggled.connect(self.toggleRF)
        layout.addWidget(RFwidget)
        layout.addWidget(widget)
        self.setLayout(layout)

    @inlineCallbacks
    def toggle(self, state):
        '''
        Sends TTL pulse to switch camera and PMT
        '''
        yield self.server.ttl_output(8, True)
        yield self.server.ttl_output(8, False)
        yield self.server.ttl_read(8)
        if 'cameraswitch' in self.settings:
            yield self.reg.set('cameraswitch', state)

    @inlineCallbacks
    def toggleRF(self, state):
        '''
        Toggles RF
        '''
        yield self.server.ttl_output(7, not state)
        if 'RFswitch' in self.settings:
            yield self.reg.set('RFswitch', state)

    def closeEvent(self, x):
        self.reactor.stop()

if __name__ == "__main__":
    a = QtGui.QApplication([])
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    cameraswitchWidget = cameraswitch(reactor)
    cameraswitchWidget.show()
    reactor.run()
