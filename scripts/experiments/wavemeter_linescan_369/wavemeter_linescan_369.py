import labrad
from labrad.units import WithUnit
from common.lib.servers.abstractservers.script_scanner.scan_methods import experiment
from twisted.internet.defer import inlineCallbacks
import time
class wavemeter_linescan_369(experiment):
    
    name = 'Wavemeter Line Scan 369'
    
    required_parameters = [('scan369', 'frequency')]
    
    def initialize(self, cxn, context, ident):
        self.ident = ident
        self.laserport = 5
        self.cxn = labrad.connect(name = '369 Wavemeter Line Scan')
        self.cxnwlm = labrad.connect('10.97.112.2', name = 'Tickle Scan')
        self.wm = self.cxnwlm.multiplexerserver  
        self.dv = self.cxn.data_vault      
        self.pv = self.cxn.parametervault
        self.pmt = self.cxn.arduino_counter
        
    def run(self, cxn, context):
        
        frequency = self.pv.get_parameter('scan369','frequency')                

        self.minval = frequency[0]
        self.maxval = frequency[1]

        
        self.dv.cd('369 Wavemeter Line Scan', True)
        self.dv.new('369 Wavemeter Line Scan',[('freq', 'Hz')], [('', 'Amplitude','kilocounts/sec')])
        window_name = ['369 Line Scan']

        self.dv.add_parameter('Window', window_name)
        self.dv.add_parameter('plotLive', True)
        self.dv.add_parameter('Frequency', frequency)

    
        self.wm.set_pid_course(self.laserport, self.minval['THz'])
        self.currentfreq = self.currentfrequency()
        self.timeout = 0
        self.waitforstart()
        tempdata = []
        if self.timeout != "too long":
            self.wm.set_pid_course(self.laserport, self.maxval['THz'])
            while self.currentfreq != self.maxval:
                counts = self.pmt.get_current_counts()
                self.currentfrequency()
                if self.currentfreq and counts:
                    tempdata.append([self.currentfreq['THz'], counts])
            tempdata.sort()
            self.dv.add(tempdata)
            
            
    def currentfrequency(self):
        self.currentfreq = WithUnit(float("%.6f" % self.wm.get_frequency(self.laserport)), 'THz')
       
    def waitforstart(self):
        self.timeout += 1
        self.currentfrequency()
        if self.currentfreq != self.minval:
            if self.timeout != 300:
                time.sleep(0.1)
                self.waitforstart()
            else: self.timeout = "too long"
        else: return None


        
    def finalize(self, cxn, context):
        self.cxn.disconnect()
        self.cxnwlm.disconnect()
            

if __name__ == '__main__':
    cxn = labrad.connect()
    scanner = cxn.scriptscanner
    exprt = wavemeter_linescan_369(cxn = cxn)
    ident = scanner.register_external_launch(exprt.name)
    exprt.execute(ident)




