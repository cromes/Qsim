from labrad.server import LabradServer, setting, Signal
from twisted.internet.defer import returnValue
from twisted.internet.threads import deferToThread
from ctypes import c_long, c_double, c_buffer, c_float, c_int, c_bool, windll, pointer
from labrad.units import WithUnit
from twisted.internet import reactor

"""
### BEGIN NODE INFO
[info]
name = Multiplexer Server
version = 1.0
description = 
instancename = Multiplexer Server

[startup]
cmdline = %PYTHON% %FILE%
timeout = 20

[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

SIGNALID1 = 122484
SIGNALID2 = 122485

class MultiplexerServer(LabradServer):
    """
    Multiplexer Server for Wavelength Meter
    """
    name = 'Multiplexerserver'
    
    expchanged  = Signal(SIGNALID1, 'signal: exposure changed', '(2i)')
    freqchanged = Signal(SIGNALID2, 'signal: frequency changed', '(iv)')
    #Set up signals to be sent to listeners
    
    def initServer(self):
        
        self.d = c_double(0)
        self.l = c_long(0)    
        self.b = c_bool(0)    
        self.wmdll = windll.LoadLibrary("C:\Windows\System32\wlmData.dll")
        #load wavemeter dll file for use of API functions self.d and self.l are dummy c_types for unused wavemeter functions
 
        self.wmdll.GetActiveChannel.restype        = c_long 
        self.wmdll.GetAmplitudeNum.restype         = c_long 
        self.wmdll.GetDeviationMode.restype        = c_bool      
        self.wmdll.GetDeviationSignalNum.restype   = c_double
        self.wmdll.GetExposureNum.restype          = c_long
        self.wmdll.GetFrequencyNum.restype         = c_double  
        self.wmdll.GetPIDCourseNum.restype         = c_long
        self.wmdll.GetSwitcherMode.restype         = c_long
        self.wmdll.GetSwitcherSignalStates.restype = c_long

        self.wmdll.SetDeviationMode.restype        = c_long
        self.wmdll.SetDeviationSignalNum.restype   = c_double
        self.wmdll.SetExposureNum.restype          = c_long 
        self.wmdll.SetPIDCourseNum.restype         = c_long              
        self.wmdll.SetSwitcherSignalStates.restype = c_long        
        self.wmdll.SetSwitcherMode.restype         = c_long
        
        #allocates c_types for dll functions
        
        self.listeners = set()

    @setting(1, "Check WLM Running")
    def instance(self,c):
        instance = self.wmdll.Instantiate
        instance.restype = c_long
        RFC = c_long(-1)    
        #RFC, reason for call, used to check if wavemeter is running (in wavemeter .h library
        status = yield instance(RFC,self.l,self.l,self.l)
        returnValue(status)

        
        
#####Main program functions        

         
    @setting(10, "Set Exposure Time", chan = 'i', ms = 'i')
    def setExposureTime(self,c,chan,ms):
        self.expchanged(chan, ms)
        ms_c = c_long(ms)
        chan_c = c_long(chan)
        yield self.wmdll.SetExposureNum(chan_c, 1,  ms_c)

        
    @setting(11, "Set Lock State", state = 'b')
    def setLockState(self,c,state):
        state_c = c_bool(state)
        yield self.wmdll.SetDeviationMode(state_c)       
        
    @setting(12, "Set Switcher Mode", mode = 'b')
    def setSwitcherMode(self, c, mode):
        mode_c = c_long(mode)
        yield self.wmdll.SetSwitcherMode(mode_c)      
        
    @setting(13, "Set Switcher Signal State", chan = 'i', state = 'b')
    def setSwitcherState(self, c, chan, state):
        chan_c = c_long(chan)
        state_c = c_long(state)
        yield self.wmdll.SetSwitcherSignalStates(chan_c, state_c, self.l)
        

        
from twisted.internet import reactor
#####Set Functions

    @setting(20, "Get Amplitude", chan = 'i', returns = 'v')
    def getAmp(self, c, chan): 
        chan_c = c_long(chan)
        amp = yield self.wmdll.GetAmplitudeNum(chan_c, c_long(2), self.l) 
        returnValue(amp)

    @setting(21, "Get Exposure", chan = 'i', returns = 'i')
    def getExp(self, c, chan): 
        chan_c = c_long(chan)
        exp = yield self.wmdll.GetExposureNum(chan_c ,1,self.l) 
        returnValue(exp)

    @setting(22,"Get Frequency", chan = 'i', returns = 'v')
    def getFrequency(self, c, chan):
        chan_c = c_long(chan)
        freq = yield self.wmdll.GetFrequencyNum(chan_c,self.d)
        self.freqchanged((chan,freq))
        #notifies listeners of changed frequency
        returnValue(freq)
        
    @setting(23, "Get Lock State")
    def getLockState(self):
        state = self.wmdll.GetDeviationMode(self.b)
        returnValue(state)
        
    @setting(24,"Get Output Voltage", chan = 'i', returns = 'v')
    def getOutputVoltage(self, c, chan):
        chan_c = c_long(chan)
        volts = yield self.wmdll.GetDeviationSignalNum(chan_c,self.d)
        returnValue(volts)  
        
    @setting(25, "Get Switcher Mode", returns = 'b')
    def getSwitcherMode(self, c):
        state = self.wmdll.GetSwitcherMode(self.l)
        returnValue(state)
    
    @setting(26, "Get Switcher Signal State", chan = 'i', returns = 'b')
    def getSwitcherState(self, c, chan):
        chan_c = c_long(chan)
        use_c = c_long(0)
        show_c = c_long(0)
        yield self.wmdll.GetSwitcherSignalStates(chan_c, pointer(use_c), pointer(show_c))
        returnValue(use_c)
        
    @inlineCallbacks    
    def measureChan(self):
        reactor.callLater(.5, self.measureChan)       
        self.getFrequency(5)
        self.getFrequency(6)
        self.getFrequency(7)
        
if __name__ == "__main__":
    from labrad import util
    util.runServer(MultiplexerServer())
    
    