# A Template NEMS Script suitable for beginners
# Please see docs/architecture.svg for a visual diagram of this code

import logging
import pickle
from pathlib import Path

import nems.analysis.api
import nems.initializers
import nems.recording as recording
import nems.uri
from nems.fitters.api import scipy_minimize
from nems.signal import RasterizedSignal

log = logging.getLogger(__name__)

# CONFIGURATION

# figure out data and results paths:
signals_dir = Path(nems.NEMS_PATH) / 'recordings'
modelspecs_dir = Path(nems.NEMS_PATH) / 'modelspecs'

# download demo data
recording.get_demo_recordings(signals_dir)
datafile = signals_dir / 'TAR010c-18-1.pkl'

# LOAD AND FORMAT RECORDING DATA

with open(datafile, 'rb') as f:
        #cellid, recname, fs, X, Y, X_val, Y_val = pickle.load(f)
        cellid, recname, fs, X, Y, epochs = pickle.load(f)
# create NEMS-format recording objects from the raw data
resp = RasterizedSignal(fs, Y, 'resp', recname, chans=[cellid])
stim = RasterizedSignal(fs, X, 'stim', recname)

# create the recording object from the signals
signals = {'resp': resp, 'stim': stim}
est = recording.Recording(signals)

val_signals = {
        'resp': RasterizedSignal(fs, Y_val, 'resp', recname, chans=[cellid]),
        'stim': RasterizedSignal(fs, X_val, 'stim', recname)}
val = recording.Recording(val_signals)


# INITIALIZE MODELSPEC

log.info('Initializing modelspec...')

# Method #1: create from "shorthand" keyword string
#modelspec_name = 'wc.18x1.g-fir.1x15-lvl.1'           # very simple linear model
#modelspec_name = 'wc.18x2.g-fir.2x15-lvl.1'         # another simple model
modelspec_name = 'wc.18x2.g-fir.2x15-lvl.1-dexp.1'  # constrain spectral tuning to be gaussian, add static output NL

# record some meta data for display and saving
meta = {'cellid': cellid,
        'batch': 271,
        'modelname': modelspec_name,
        'recording': cellid
        }
modelspec = nems.initializers.from_keywords(modelspec_name, meta=meta)

# RUN AN ANALYSIS

# GOAL: Fit your model to your data, producing the improved modelspecs.
#       Note that: nems.analysis.* will return a list of modelspecs, sorted
#       in descending order of how they performed on the fitter's metric.

log.info('Fitting modelspec...')

if 'nonlinearity' in modelspec[-1]['fn']:
        # quick fit linear part first to avoid local minima
        modelspec = nems.initializers.prefit_LN(
                est, modelspec, tolerance=1e-4, max_iter=500)

# then fit full nonlinear model
modelspec = nems.analysis.api.fit_basic(est, modelspec, fitter=scipy_minimize)

# GENERATE SUMMARY STATISTICS

log.info('Generating summary statistics...')

# generate predictions
est, val = nems.analysis.api.generate_prediction(est, val, modelspec)

# evaluate prediction accuracy
modelspec = nems.analysis.api.standard_correlation(est, val, modelspec)

log.info("Performance: r_fit={0:.3f} r_test={1:.3f}".format(
        modelspec.meta['r_fit'][0][0],
        modelspec.meta['r_test'][0][0]))

# SAVE YOUR RESULTS

# uncomment to save model to disk
# logging.info('Saving Results...')
# modelspec.save_modelspecs(modelspecs_dir, modelspecs)

# GENERATE PLOTS

# GOAL: Plot the predictions made by your results vs the real response.
#       Compare performance of results with other metrics.

log.info('Generating summary plot...')

# Generate a summary plot
fig = modelspec.quickplot(rec=est)
fig.show()

# Optional: uncomment to save your figure
# fname = nplt.save_figure(fig, modelspecs=modelspecs, save_dir=modelspecs_dir)

# uncomment to browse the validation data
#from nems.gui.editors import EditorWindow
#ex = EditorWindow(modelspec=modelspec, rec=val)

# TODO SHARE YOUR RESULTS

# GOAL: Upload your resulting models so that you can see how well your model
#       did relative to other peoples' models. Save your results to a DB.
