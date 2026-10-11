"""Read-only benchmark backends. Inputs contain no scenario/plant/injection truth."""
from dataclasses import dataclass
import numpy as np

CHANNELS = ('timing', 'communication', 'memory', 'sensor_control', 'actuator', 'plant')
ORIGINS = ('MEMORY', 'TIMING', 'COMMUNICATION', 'SENSOR_CONTROL', 'ACTUATOR')
WEIGHTS = ((1, 1, 1, 1, 1, 1), (2, 2, 2, 1, 2, 1))
THRESHOLDS = (.04, .06, .08, .10, .14, .18)

@dataclass(frozen=True)
class Evidence:
    time_ms: np.ndarray
    strength: np.ndarray
    available: np.ndarray
    origin_subset: np.ndarray

    def __post_init__(self):
        n = len(self.time_ms)
        assert self.strength.shape == self.available.shape == self.origin_subset.shape == (n, 6)
        assert np.all(np.diff(self.time_ms) > 0)
        assert np.isfinite(self.strength).all() and np.all((self.strength >= 0) & (self.strength <= 1))

    @property
    def values(self):
        return np.where(self.available, self.strength, 0.)

    @property
    def features(self):
        # Unavailable values are masked AND explicitly identified; no truth or time.
        return np.column_stack((self.values, self.available.astype(float)))


def unambiguous(e, qualifying):
    subsets = np.where(qualifying, e.origin_subset, 0)
    union = np.bitwise_or.reduce(subsets, axis=1)
    # Uninformative plant-origin evidence cannot identify a component.
    ambiguous = np.any(qualifying & (e.origin_subset == 31), axis=1)
    return np.where((union > 0) & ((union & (union - 1)) == 0) & ~ambiguous, union, 0)


def simple_or(e):
    qualified = e.available & (e.strength >= .5)  # Existing provider criterion.
    return qualified.any(axis=1), unambiguous(e, qualified)


def weighted_sum(e, weights, threshold):
    w = np.asarray(weights) * e.available
    score = np.divide((w * e.values).sum(axis=1), w.sum(axis=1),
                      out=np.zeros(len(w)), where=w.sum(axis=1) > 0)
    # Conventional dominant instantaneous contributor; no temporal origin rules.
    contributions = w * e.values
    top = contributions.argmax(axis=1)
    ordered = np.sort(contributions, axis=1)
    total = contributions.sum(axis=1)
    confidence = np.divide(ordered[:, -1], total, out=np.zeros(len(w)), where=total > 0)
    margin = np.divide(ordered[:, -1] - ordered[:, -2], total,
                       out=np.zeros(len(w)), where=total > 0)
    origin = e.origin_subset[np.arange(len(w)), top]
    origin = np.where((confidence >= .55) & (margin >= .15) & ((origin & (origin - 1)) == 0), origin, 0)
    return score >= threshold, origin


def plain_ds(e):
    # Simple-support BPAs: m(ABNORMAL)=e, m(Theta)=1-e. Independent channel
    # combination gives Bel(A)=1-product(1-e). Zero is vacuous, not NORMAL.
    values = e.values
    belief = 1 - np.prod(1 - values, axis=1)
    n = len(values)
    mass = np.zeros((n, 32)); mass[:, 31] = 1
    conflict_failure = np.zeros(n, dtype=bool)
    for i in range(6):
        p = values[:, i]
        target = e.origin_subset[:, i]
        out = mass * (1 - p[:, None])
        for subset in range(1, 32):
            np.add.at(out, (np.arange(n), subset & target), mass[:, subset] * p)
        norm = 1 - out[:, 0]
        failed = norm <= 1e-12
        out[:, 0] = 0
        out = np.divide(out, norm[:, None], out=np.zeros_like(out), where=norm[:, None] > 1e-12)
        out[failed, 31] = 1
        conflict_failure |= failed
        mass = out
    betp = np.zeros((n, 5))
    for subset in range(1, 32):
        for j in range(5):
            if subset & (1 << j):betp[:, j] += mass[:, subset] / subset.bit_count()
    order = np.sort(betp, axis=1)
    valid = (order[:, -1] >= .55) & (order[:, -1] - order[:, -2] >= .15) & (mass[:, 31] <= .5) & ~conflict_failure
    origin = np.where(valid, 1 << betp.argmax(axis=1), 0)
    return belief >= .5, origin


def svm_predict(e, model):
    # Deduplication changes computation cost only, never sequence semantics.
    unique, inverse = np.unique(e.features, axis=0, return_inverse=True)
    alarm = model.predict(unique)[inverse].astype(bool)
    return alarm, np.zeros(len(alarm), dtype=int)
