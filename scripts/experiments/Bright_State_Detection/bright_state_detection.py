import labrad
from Qsim.scripts.pulse_sequences.bright_state_preperation import bright_state_preperation as sequence
from Qsim.scripts.pulse_sequences.bright_state_preperation_interleaved import bright_state_preperation_interleaved as interleaved_sequence
from Qsim.scripts.experiments.qsimexperiment import QsimExperiment
import numpy as np


class BrightStateDetection(QsimExperiment):
    """
    Doppler cool ion the readout bright fidelity
    """

    name = 'Bright State Detection'

    exp_parameters = []
    exp_parameters.append(('BrightStateDetection', 'RunContinuous'))
    exp_parameters.append(('Modes', 'state_detection_mode'))
    exp_parameters.append(('ShelvingStateDetection', 'repititions'))
    exp_parameters.append(('StandardStateDetection', 'repititions'))
    exp_parameters.append(('StandardStateDetection', 'points_per_histogram'))
    exp_parameters.append(('StandardStateDetection', 'state_readout_threshold'))
    exp_parameters.append(('ShelvingDopplerCooling', 'doppler_counts_threshold'))
    exp_parameters.extend(sequence.all_required_parameters())

    def initialize(self, cxn, context, ident):
        self.ident = ident
        self.pulser = self.cxn.pulser
        self.rsg = self.cxn.grapher
        self.prob_ctx = self.dv.context()
        self.hist_ctx = self.dv.context()

    def run(self, cxn, context):

        self.setup_prob_datavault()
        if self.p.BrightStateDetection.RunContinuous is True:
            i = 0
            if self.p.BrightStateDetection.InterleavedSequence == 'Off':
                self.program_pulser(sequence)
            elif self.p.BrightStateDetection.InterleavedSequence == 'On':
                self.program_pulser(interleaved_sequence)
            while True:
                i += 1
                if self.p.Modes.state_detection_mode == 'Shelving':
                    [counts_doppler_bright, counts_bright] = self.run_sequence(max_runs=500, num=2)
                    bright_errors = np.where(counts_doppler_bright <= self.p.ShelvingDopplerCooling.doppler_counts_threshold)
                    counts_bright = np.delete(counts_bright, bright_errors)

                    print 'Bright Doppler Errors:', len(bright_errors[0])
                    counts = counts_bright

                hist = self.process_data(counts)
                if i % self.p.StandardStateDetection.points_per_histogram == 0:
                    self.setup_hist_datavault()
                    self.plot_hist(hist)
                self.plot_prob(i, counts)
                should_break = self.update_progress(np.random.random())
                if should_break:
                    break
                old_params = dict(self.p.iteritems())
                self.reload_all_parameters()
                self.p = self.parameters
                if self.p != old_params:
                    self.program_pulser(sequence)
        else:
            counts = self.program_pulser()
            hist = self.process_data(counts)
            self.setup_hist_datavault()
            self.plot_hist(hist)
            self.plot_prob(0, hist)

    def setup_hist_datavault(self):
        self.dv.cd(['', 'Bright_State_Detection'],
                   True, context=self.hist_ctx)
        self.dataset_hist = self.dv.new('bright_state_prep',
                                        [('run', 'arb u')],
                                        [('Counts', 'Counts', 'num')],
                                        context=self.hist_ctx)
        for parameter in self.p:
            self.dv.add_parameter(parameter,
                                  self.p[parameter], context=self.hist_ctx)

    def setup_prob_datavault(self):
        self.dv.cd(['', 'Bright_State_Probability'],
                   True, context=self.prob_ctx)
        self.dataset_prob = self.dv.new('fidelity_bright_state_prep',
                                        [('run', 'arb u')],
                                        [('Counts', 'Counts', 'num')],
                                        context=self.prob_ctx)

        self.rsg.plot(self.dataset_prob, 'Fidelity', False)
        for parameter in self.p:
            self.dv.add_parameter(parameter, self.p[parameter],
                                  context=self.prob_ctx)

    def plot_hist(self, hist):
        self.dv.add(hist, context=self.hist_ctx)
        self.rsg.plot(self.dataset_hist, 'Histogram', False)

    def plot_prob(self, num, counts):
        prob = self.get_pop(counts)
        self.dv.add(num, prob, context=self.prob_ctx)


if __name__ == '__main__':
    cxn = labrad.connect()
    scanner = cxn.scriptscanner
    exprt = BrightStateDetection(cxn=cxn)
    ident = scanner.register_external_launch(exprt.name)
    exprt.execute(ident)
