from common.lib.servers.Pulser2.pulse_sequences.pulse_sequence import pulse_sequence
from sub_sequences.shelving_doppler_cooling import shelving_doppler_cooling
from sub_sequences.state_detection.shelving_state_detection import shelving_state_detection
from sub_sequences.shelving import shelving
from sub_sequences.optical_pumping import optical_pumping
from sub_sequences.microwave_interrogation.microwave_interrogation import microwave_interrogation
from sub_sequences.deshelving import deshelving
from sub_sequences.turn_off_all import turn_off_all


class shelving_dark_spam(pulse_sequence):

    required_subsequences = [shelving, shelving_doppler_cooling, shelving_state_detection, deshelving,
                             optical_pumping, microwave_interrogation, turn_off_all]

    required_parameters = [
                           ]

    def sequence(self):
        self.addSequence(turn_off_all)
        self.addSequence(shelving_doppler_cooling)
        self.addSequence(optical_pumping)
        self.addSequence(microwave_interrogation)
        self.addSequence(shelving)
        self.addSequence(shelving_state_detection)
        self.addSequence(deshelving)
