"""Standard binary backends on shared, bounded runtime provider evidence.

No scenario, fault label, plant outcome, or CLOVER decision enters inference.
Provider strengths already contain the frozen physical preprocessing.
"""
import numpy as np


def ewma(values, alpha):
    """Zero-initialized causal EWMA per channel, maximum across channels."""
    v = np.asarray(values, dtype=float)
    if not 0 < alpha <= 1:
        raise ValueError('alpha must be in (0, 1]')
    state = np.zeros(v.shape[1]); out = np.empty(len(v))
    for i, row in enumerate(v):
        state = alpha*row + (1-alpha)*state
        out[i] = state.max()
    return out


def cusum(values, allowance):
    """One-sided Page CUSUM S_t=max(0,S_(t-1)+e_t-k), per channel.

    Inputs are nonnegative anomaly strengths, not signed physical residuals.
    Unavailable input is zero (decay by k); state resets between runs.
    """
    v = np.asarray(values, dtype=float)
    if allowance <= 0:
        raise ValueError('allowance must be positive')
    cumulative = np.cumsum(v - allowance, axis=0)
    minimum = np.minimum.accumulate(np.vstack((np.zeros((1,v.shape[1])), cumulative)), axis=0)[1:]
    return (cumulative-minimum).max(axis=1)


def weighted_score(e, weights):
    w = np.asarray(weights, dtype=float) * e.available
    return np.divide((w*e.values).sum(axis=1), w.sum(axis=1),
                     out=np.zeros(len(w)), where=w.sum(axis=1)>0)


def detect_edges(score, threshold, time_ms, start_ms):
    """Same strict-threshold rising-edge convention used by new baselines."""
    alarm = np.asarray(score) > threshold
    edges = alarm & ~np.r_[False, alarm[:-1]]
    return bool(np.any(edges & (np.asarray(time_ms)>=start_ms))), bool(alarm.any())
