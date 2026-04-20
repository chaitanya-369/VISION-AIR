import time
import numpy as np

class LowPassFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.prev_value = None

    def filter(self, value, alpha=None):
        if alpha is None:
            alpha = self.alpha
        if self.prev_value is None:
            self.prev_value = value
            return value
        filtered = alpha * value + (1 - alpha) * self.prev_value
        self.prev_value = filtered
        return filtered

class OneEuroFilter:
    def __init__(self, freq, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filter = LowPassFilter(self.alpha(min_cutoff))
        self.dx_filter = LowPassFilter(self.alpha(d_cutoff))
        self.last_time = None

    def alpha(self, cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x):
        curr_time = time.time()
        if self.last_time is None:
            self.last_time = curr_time
            return x
        
        dt = curr_time - self.last_time
        if dt <= 0:
            return x
        
        self.freq = 1.0 / dt
        self.last_time = curr_time

        # Filter velocity to compute dynamic cutoff
        prev_x = self.x_filter.prev_value
        dx = (x - prev_x) / dt if prev_x is not None else 0
        edx = self.dx_filter.filter(dx)
        
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filter.filter(x, self.alpha(cutoff))

    # Note: I noticed a bug in my previous implementation, 
    # LowPassFilter.filter only takes one arg but I need it to use the dynamic alpha.
    # Let me fix LowPassFilter to allow dynamic alpha.

