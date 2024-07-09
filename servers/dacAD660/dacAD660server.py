"""
### BEGIN NODE INFO
[info]
name = DAC AD660 Server
version = 1.0
description =
instancename = DAC AD660 Server
[startup]
cmdline = %PYTHON% %FILE%
timeout = 20
[shutdown]
message = 987654321
timeout = 20
### END NODE INFO
"""

from labrad.server import LabradServer, setting, Signal
from api import API
from config.dac_ad660_config import HardwareConfiguration as HC

SERVERNAME = 'DAC AD660 Server'
SIGNALID = 270837


class Voltage:
    """
    A representation of a voltage,
    with the capability to compile down to the hex representation that the DAC board needs
    """

    def __init__(self, channel, analog_voltage=None, digital_voltage=None):
        self.channel = channel
        self.digital_voltage = digital_voltage
        self.analog_voltage = analog_voltage

    def program(self, set_num):
        """
        Compute the hex code to program this voltage
        """
        self.set_num = set_num
        if self.analog_voltage is not None:
            (vMin, vMax) = self.channel.allowed_voltage_range
            if self.analog_voltage < vMin:
                self.analog_voltage = vMin
            if self.analog_voltage > vMax:
                self.analog_voltage = vMax
            self.digital_voltage = self.compute_digital_voltage(self.analog_voltage)
        self.hex_rep = self.__get_hex_rep()

    def compute_digital_voltage(self, analog_voltage):
        """
        Returns an integer representation of a given analog voltage.
        If the DAC is 16-bit:
            - 0    is the minimum voltage
            - 2^15 is zero volts
            - 2^16 is the maximum voltage
        """
        v_min, v_max = self.channel.board_voltage_range
        zero_value = 2 ** (HC.PREC_BITS - 1)
        number_of_voltages = 2 ** HC.PREC_BITS
        return int(round(zero_value + analog_voltage * number_of_voltages / (v_max - v_min)))

    def __get_hex_rep(self) -> bytearray:
        """
        returns a 4-byte bytearray.
        - The first 16 bits correspond to the DAC voltage (an integer from 0 (-10V) to 2^16 (+10V)).
        - The next 5 bits correspond to the port number (0 to 32)
        - the next 10 bits correspond to the queue position (?) usually a low value
        - plus one trailing 0 to pad it out into 4 bytes

        Then these bytes are rearranged to be little-endian:
        voltage bytes are reversed, and control bytes are reversed
        """
        port = bin(self.channel.dac_channel_number)[2:].zfill(5)
        if HC.pulseTriggered:
            set_n = bin(self.set_num)[2:].zfill(10)
        else:
            set_n = bin(1)[2:].zfill(10)
        voltage = bin(self.digital_voltage)[2:].zfill(16)
        big = voltage + port + set_n + '0'
        rep = [int(big[8:16], 2), int(big[:8], 2), int(big[24:32], 2), int(big[16:24], 2)]

        return bytearray(rep)


class Queue(object):
    def __init__(self):
        self.current_set = 1
        self.set_dict = {i: [] for i in range(1, HC.maxCache + 1)}

    def advance(self):
        self.current_set = (self.current_set % HC.maxCache) + 1

    def reset(self):
        self.current_set = 1

    def insert(self, v):
        """ Always insert voltages to the current queue position, takes a voltage object """
        v.program(self.current_set)
        self.set_dict[self.current_set].append(v)

    def get(self):
        v = self.set_dict[self.current_set].pop(0)
        return v

    def clear(self):
        self.current_set = 1
        self.set_dict = {i: [] for i in range(1, HC.maxCache + 1)}


class DACServer(LabradServer):
    """
    DAC Server
    Used for controlling DC trap electrodes
    """
    name = SERVERNAME
    onNewUpdate = Signal(SIGNALID, 'signal: ports updated', 's')
    queue = Queue()
    api = API()

    registry_path = ['', 'Servers', HC.EXPNAME + SERVERNAME]
    dac_dict = HC.elec_dict
    current_voltages = {}
    listeners = set()

    def initServer(self):
        self.registry = self.client.registry
        self.initialize_board()
        # yield self.setCalibrations()

    def initialize_board(self):
        connected = self.api.connect_ok_board()
        if not connected:
            raise Exception("FPGA Not Found")

    @setting(4, "Set Individual Digital Voltages", digital_voltages='*(si)')
    def set_individual_digital_voltages(self, c, digital_voltages):
        """
        Pass a list of tuples of the form:
        (portNum, newVolts)
        """
        for (port, dv) in digital_voltages:
            self.queue.insert(Voltage(self.dac_dict[port], digital_voltage=dv))
        yield self.write_to_fpga(c)

    @setting(5, "Set Individual Analog Voltages", analog_voltages='*(sv)')
    def set_individual_analog_voltages(self, c, analog_voltages):
        """
        Pass a list of tuples of the form:
        (portNum, newVolts)
        """
        for (port, av) in analog_voltages:
            self.queue.insert(Voltage(self.dac_dict[port], analog_voltage=av))
        yield self.write_to_fpga(c)

    def write_to_fpga(self, c):
        self.api.reset_fifo_dac()
        for i in range(len(self.queue.set_dict[self.queue.current_set])):
            v = self.queue.get()
            self.api.set_dac_voltage(v.hex_rep)
            # print("DAC voltage set in API")
            if v.channel.name in HC.elec_dict.keys():
                self.current_voltages[v.channel.name] = v.analog_voltage
        if c is not None:
            self.notify_other_listeners(c)

    @setting(9, "Get Analog Voltages", returns='*(sv)')
    def get_current_voltages(self, c):
        """
        Return the current voltage
        """
        return list(self.current_voltages.items())

    @setting(14, "Get DAC Channel Name", port_number='i', returns='s')
    def get_dac_channel_name(self, c, port_number):
        """
        Return the channel name for a given port number.
        """
        for key in self.dac_dict.keys():
            if self.dac_dict[key].dac_channel_number == port_number:
                return key

    @setting(17, "get queue")
    def get_queue(self, c):
        return self.queue.current_set

    def initContext(self, c):
        self.listeners.add(c.ID)

    def expireContext(self, c):
        self.listeners.remove(c.ID)

    def notify_other_listeners(self, context):
        notified = self.listeners.copy()
        try:
            notified.remove(context.ID)
        except Exception:
            pass
        self.onNewUpdate('Channels updated', notified)


if __name__ == "__main__":
    from labrad import util

    util.runServer(DACServer())
