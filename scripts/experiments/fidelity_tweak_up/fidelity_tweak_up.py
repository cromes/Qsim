import labrad
from Qsim.scripts.pulse_sequences.fidelity_tweak_up import fidelity_tweak_up as sequence
from Qsim.scripts.experiments.qsimexperiment import QsimExperiment
import numpy as np


class fidelity_tweak_up(QsimExperiment):
    """
    Doppler cool ion the readout bright fidelity,
    readout darkstate and subtract
    """

    name = 'Fidelity Tweak Up'

    exp_parameters = []
    exp_parameters.append(('StateDetection', 'repititions'))
    exp_parameters.append(('StateDetection', 'state_readout_threshold'))
    exp_parameters.append(('StateDetection', 'points_per_histogram'))
    exp_parameters.extend(sequence.all_required_parameters())

    def initialize(self, cxn, context, ident):
        self.ident = ident
        self.prob_ctx = self.dv.context()
        self.hist_ctx = self.dv.context()

    def run(self, cxn, context):

        self.setup_prob_datavault()
        i = 0
        self.program_pulser(sequence)
        while True:
            i += 1
            counts = self.run_sequence(max_runs=500)
            counts_bright = counts[0::2]
            counts_dark = counts[1::2]
            hist_dark = self.process_data(counts_dark)
            hist_bright = self.process_data(counts_bright)
            if i % int(self.p.StateDetection.points_per_histogram) == 0:
                self.setup_hist_datavault('Dark')
                self.plot_hist(hist_dark)
                self.setup_hist_datavault('Bright')
                self.plot_hist(hist_bright)
            self.plot_prob(i, counts_bright, counts_dark)
            should_break = self.update_progress(np.random.random())
            old_params = dict(self.p.iteritems())
            if should_break:
                break
            self.reload_all_parameters()
            self.p = self.parameters
            if self.p != old_params:
                self.program_pulser(sequence)

    def setup_hist_datavault(self, state):
        self.dv.cd(['', state + '_State_Detection'],
                   True, context=self.hist_ctx)
        self.dataset_hist = self.dv.new(state + '_state_prep',
                                        [('run', 'arb u')],
                                        [('Counts', 'Counts', 'num')],
                                        context=self.hist_ctx)
        for parameter in self.p:
            self.dv.add_parameter(parameter,
                                  self.p[parameter], context=self.hist_ctx)

    def setup_prob_datavault(self):
        self.dv.cd(['', 'fidelity_tweak_up'], True, context=self.prob_ctx)

        self.dataset_prob = self.dv.new('fidelity_tweak_up', [('run', 'prob')],
                                        [('Prob', 'bright_prep', 'num'),
                                         ('Prob', 'dark_prep', 'num'),
                                         ('Prob', 'contrast', 'num')],
                                        context=self.prob_ctx)
        self.grapher.plot(self.dataset_prob, 'Fidelity', False)
        for parameter in self.p:
            self.dv.add_parameter(parameter, self.p[parameter],
                                  context=self.prob_ctx)

    def plot_hist(self, hist):
        self.dv.add(hist, context=self.hist_ctx)
        self.grapher.plot(self.dataset_hist, 'Histogram', False)

    def plot_prob(self, num, counts_dark, counts_bright):
        prob_dark = self.get_pop(counts_dark)
        prob_bright = self.get_pop(counts_bright)
        self.dv.add(num, prob_dark, prob_bright,
                    prob_bright - prob_dark, context=self.prob_ctx)


if __name__ == '__main__':
    cxn = labrad.connect()
    scanner = cxn.scriptscanner
    exprt = fidelity_tweak_up(cxn=cxn)
    ident = scanner.register_external_launch(exprt.name)
    exprt.execute(ident)
