import labrad
from Qsim.scripts.pulse_sequences.microwave_point import microwave_point as sequence
from Qsim.scripts.experiments.qsimexperiment import QsimExperiment
from labrad.units import WithUnit as U
import numpy as np


class MicrowaveRabiFlopping(QsimExperiment):
    """
    repeatedly prepare the |0> state, interrogate with resonant microwaves for
    a variable time t and measure the population in the bright state
    """

    name = 'Microwave Rabi Flopping'

    exp_parameters = []
    exp_parameters.append(('RabiFlopping', 'scan'))
    exp_parameters.append(('DopplerCooling', 'detuning'))
    exp_parameters.append(('Transitions', 'main_cooling_369'))

    exp_parameters.append(('Modes', 'state_detection_mode'))
    exp_parameters.append(('ShelvingStateDetection', 'repititions'))
    exp_parameters.append(('StandardStateDetection', 'repititions'))
    exp_parameters.append(('StandardStateDetection', 'points_per_histogram'))
    exp_parameters.append(('StandardStateDetection', 'state_readout_threshold'))
    exp_parameters.append(('Shelving_Doppler_Cooling', 'doppler_counts_threshold'))
    exp_parameters.append(('MicrowaveInterogation', 'AC_line_trigger'))

    exp_parameters.extend(sequence.all_required_parameters())

    exp_parameters.remove(('MicrowaveInterogation', 'duration'))

    def initialize(self, cxn, context, ident):
        self.ident = ident
        self.pulser = cxn.pulser

    def run(self, cxn, context):
        self.pulser.switch_auto('MicrowaveTTL')
        self.pulser.switch_auto('MicrowaveTTL3')

        qubit = self.p.Line_Selection.qubit
        mode = self.p.Modes.state_detection_mode

        init_bright_state_pumping_method = self.p.BrightStatePumping.method
        init_microwave_pulse_sequence = self.p.MicrowaveInterogation.pulse_sequence
        init_optical_pumping_method = self.p.OpticalPumping.method

        self.p['BrightStatePumping.method'] = 'Microwave'
        #self.p['MicrowaveInterogation.pulse_sequence'] = 'standard'

        init_line_trigger_state = self.p.MicrowaveInterogation.AC_line_trigger
        self.pulser.line_trigger_state(False)

        self.setup_datavault('time', 'probability')  # gives the x and y names to Data Vault
        self.setup_grapher('Rabi Flopping ' + qubit)
        self.times = self.get_scan_list(self.p.RabiFlopping.scan, 'us')
        for i, duration in enumerate(self.times):
            should_break = self.update_progress(i/float(len(self.times)))
            if should_break:
                break
            self.p['MicrowaveInterogation.duration'] = U(duration, 'us')

            if mode == 'Standard':
                # force standard optical pumping if standard readout method used
                # no sense in quadrupole optical pumping by accident if using standard readout
                self.p['OpticalPumping.method'] = 'Standard'

            self.program_pulser(sequence)

            if mode == 'Shelving':
                [doppler_counts, detection_counts] = self.run_sequence(max_runs=500, num=2)
                errors = np.where(doppler_counts <= self.p.Shelving_Doppler_Cooling.doppler_counts_threshold)
                counts = np.delete(detection_counts, errors)
            elif mode == 'Standard':
                [counts] = self.run_sequence()
            else:
                print 'Detection mode not selected!!!'

            if i % self.p.StandardStateDetection.points_per_histogram == 0:
                hist = self.process_data(counts)
                self.plot_hist(hist)

            pop = self.get_pop(counts)
            self.dv.add(duration, pop)

        # reset all the init settings that you forced for this experiment 
        self.p['BrightStatePumping.method'] = init_bright_state_pumping_method
        self.p['MicrowaveInterogation.pulse_sequence'] = init_microwave_pulse_sequence
        self.p['OpticalPumping.method'] = init_optical_pumping_method
        if init_line_trigger_state == 'On':
            self.pulser.line_trigger_state(True)

    def finalize(self, cxn, context):
        self.pulser.switch_manual('MicrowaveTTL')
        self.pulser.switch_manual('MicrowaveTTL3')


if __name__ == '__main__':
    cxn = labrad.connect()
    scanner = cxn.scriptscanner
    exprt = MicrowaveRabiFlopping(cxn=cxn)
    ident = scanner.register_external_launch(exprt.name)
    exprt.execute(ident)
