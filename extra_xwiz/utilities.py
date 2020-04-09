"""Utilities"""

from getpass import getuser
from glob import glob
import numpy as np
from scipy.optimize import curve_fit
import subprocess
import time


def estimate_moments(sample):
    """Calculate the 'naive' height, mean and stddev of a sample,
       to serve as starting values (estimates) for a Gauss fit.
    """
    return np.max(sample), np.mean(sample), np.std(sample)


def print_hist_bars(bins, freqs, length=80, fill='■'):
    scale_factor = float(length) / max(freqs)
    for i, freq in enumerate(freqs):
        bar = fill * (int(scale_factor) * freq)
        print('{:6.2f} {}'.format(bins[i], bar))


def gauss_func(x, *p):
    amp, mu, sigma = p       # unpack parameters: amplitude, mean, stddev
    return amp * np.exp(-(x - mu)**2/(2.*sigma**2))


def fit_gauss_curve(sample):
    """Fit a Gaussian as model function to observed distribution data,
       which are derived from a sample by histogram-binning
       """
    p0 = estimate_moments(sample)
    y, bins = np.histogram(sample, bins=10)  # y: frequency (not density)
    x = (bins[:-1] + bins[1:]) / 2  # take bin centres as x
    print_hist_bars(x, y, length=50)
    p, var_matrix = curve_fit(gauss_func, x, y, p0=p0)
    print(p)
    return p[1]


def seconds(tm_str):
    units = tm_str.split(':')
    secs = 0
    for i in range(len(units)):
        j = len(units) - 1 - i
        secs += int(units[j]) * pow(60, i)
    # print(secs)
    return secs


def print_progress_bar(i, n, length=80, fill='█'):
    percent = '{0:.1f}'.format(100 * (i / float(n)))
    filled_len = int(length * i // n)
    bar = fill * filled_len + '-' * (length - filled_len)
    print('\r Progress: |%s| %s%% complete' % (bar, percent), end='\r')


def calc_progress(out_logs, n_total):
    n_current = []
    for log in out_logs:
        with open(log, "r") as f:
            ll = f.readlines()
        if 'indexable' in ll[-1]:
            # print(log, ll[-1].split()[4])
            n_current.append(int(ll[-1].split()[4]))
        elif 'Final:' in ll[-1]:
            n_current.append(n_total)
    if len(n_current) > 0:
        n_slowest = min(n_current)
        print_progress_bar(n_slowest, n_total, length=50)


def wait_or_cancel(job_id, n_nodes, n_total, time_limit):
    """ Loop until queue is empty or time-limit reached """
    print(' Waiting for job-array', job_id)
    time.sleep(3)
    out_logs = glob('slurm-*.out')
    max_time = '0:00'
    n_tasks = n_nodes
    while n_tasks > 0 and seconds(max_time) <= seconds(time_limit):
        queue = subprocess.check_output(['squeue', '-u', getuser()])
        tasks = queue.decode('utf-8').split('\n')
        n_tasks = len(tasks) - 2   # header-line + trailing '\n' always present
        times = [ln.split()[5] for ln in tasks[1:-1]]
        if n_tasks > 0:
            max_time = max(times)
        calc_progress(out_logs, (n_total / n_nodes))
        time.sleep(1)


def cell_in_tolerance(constants, reference):
    const_name = ['a', 'b', 'c', 'al', 'be', 'ga']
    refr_value = []
    with open(reference, 'r') as f:
        for ln in f:
            if ' = ' not in ln:
                continue
            if ln.split()[0] in const_name:
                refr_value.append(float(ln.split()[2]))
    for i in range(6):
        if constants[i] < 0.95 * refr_value[i]:
            return False
        if constants[i] > 1.05 * refr_value[i]:
            return False
    return True

