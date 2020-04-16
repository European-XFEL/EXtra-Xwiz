"""Utilities"""

from getpass import getuser
from glob import glob
import numpy as np
from scipy.optimize import curve_fit
import subprocess
import time


def estimate_moments(sample):
    """ Calculate the 'naive' height, mean and stddev of a sample,
        to serve as starting values (estimates) for a Gauss fit.
    """
    return len(sample)//2, np.mean(sample), np.std(sample)


def print_hist_bars(bins, freqs, length=80, fill='■'):
    """ Visualize histogram frequencies as bars, scaled in line-length
    """
    scale_factor = float(length) / max(freqs)
    for i, freq in enumerate(freqs):
        bar = fill * int(scale_factor * freq)
        print('{:6.2f} {}'.format(bins[i], bar))


def gauss_func(x, *p):
    """ Parametric expression of the Gauss equation
    """
    amp, mu, sigma = p       # unpack parameters: amplitude, mean, stddev
    return amp * np.exp(-(x - mu)**2/(2.*sigma**2))


def fit_gauss_curve(sample):
    """ Fit a Gaussian model function to observed distribution data,
        which are derived from a sample by histogram-binning
    """
    p0 = estimate_moments(sample)
    print(p0)
    y, bins = np.histogram(sample, bins=10)  # y: frequency (not density)
    x = (bins[:-1] + bins[1:]) / 2  # take bin centres as x
    print_hist_bars(x, y, length=50)
    p, var_matrix = curve_fit(gauss_func, x, y, p0=p0)
    print(p)
    return p[1]


def seconds(tm_str):
    """ Convert a time string HH:MM:SS to integer-number seconds
    """
    units = tm_str.split(':')
    secs = 0
    for i in range(len(units)):
        j = len(units) - 1 - i
        secs += int(units[j]) * pow(60, i)
    # print(secs)
    return secs


def print_progress_bar(i, n, length=80, fill='█'):
    """ Visualize a percent fraction by a bar, update in-line using CR char.
    """
    percent = '{0:.1f}'.format(100 * (i / float(n)))
    filled_len = int(length * i // n)
    bar = fill * filled_len + '-' * (length - filled_len)
    print('\r Progress: |%s| %s%% complete. ' % (bar, percent), end='\r')


def calc_progress(out_logs, n_total):
    """ Compare total number of processed frames (from logs) at a given time
        to the overall total number of frames to process.
    """
    n_current = []
    for log in out_logs:
        with open(log, "r") as f:
            ll = f.readlines()
        if 'indexable' in ll[-1]:
            # print(log, ll[-1].split()[4])
            n_current.append(int(ll[-1].split()[4]))
        elif 'Final:' in ll[-1]:
            n_current.append(int(ll[-1].split()[1]))
    if len(n_current) > 0:
        n_current_total = sum(n_current)
        print_progress_bar(n_current_total, n_total, length=50)


def wait_or_cancel(job_id, n_nodes, n_total, time_limit):
    """ Loop until queue is empty or time-limit reached
    """
    print(' Waiting for job-array', job_id)
    out_logs = []
    # wait until all tasks have passed queueing stage and N(logs) == N(tasks)
    while len(out_logs) < n_nodes:
        time.sleep(3)
        out_logs = glob(f'slurm-{job_id}_*.out')
    max_time = '0:00'
    n_tasks = n_nodes
    # wait until all tasks have finished, hence vanished from the squeue list
    while n_tasks > 0 and seconds(max_time) <= seconds(time_limit):
        queue = subprocess.check_output(['squeue', '-u', getuser()])
        tasks = queue.decode('utf-8').split('\n')
        n_tasks = len(tasks) - 2   # header-line + trailing '\n' always present
        times = [ln.split()[5] for ln in tasks[1:-1]]
        if n_tasks > 0:
            max_time = max(times)
        calc_progress(out_logs, n_total)
        time.sleep(1)
    print()


def cell_in_tolerance(probe_constants, reference_file):
    """Compare cell constants of one crystal from indexing with expectation
    """
    const_names = ['a', 'b', 'c', 'al', 'be', 'ga']
    reference_value = []
    with open(reference_file, 'r') as f:
        for ln in f:
            if ' = ' not in ln:
                continue
            if ln.split()[0] in const_names:
                reference_value.append(float(ln.split()[2]))
    for i in range(6):
        if probe_constants[i] < 0.9 * reference_value[i]:
            return False
        if probe_constants[i] > 1.1 * reference_value[i]:
            return False
    return True


def get_crystal_frames(stream_file, cell_file):
    """ Parse stream file after indexamajig run.
        Check crystals of indexed frames; if they match a prior expectation,
        add event number (frame) and cell constants to respective lists.
    """
    hit_list = []
    cell_ensemble = []
    with open(stream_file, 'r') as f:
        for ln in f:
            if 'Event:' in ln:
                event = ln.split()[-1]  # includes '//'
            if 'Cell parameters' in ln:
                cell_edges = [(10 * float(x)) for x in ln.split()[2:5]]
                cell_angles = [float(x) for x in ln.split()[6:9]]
                cell_constants = cell_edges + cell_angles
                if not cell_in_tolerance(cell_constants, cell_file):
                    continue
                cell_ensemble.append(cell_constants)
                hit_list.append(event)
    print(len(hit_list), 'frames with (reasonable) crystals found')
    return hit_list, cell_ensemble


def fit_unit_cell(ensemble):
    """ Loop over separate lists of six unit cell constants, fit each
        assuming a Gaussian distribution of values.
    """
    constant_name = ['a', 'b', 'c', 'alpha', 'beta', 'gamma']
    distributed_parms = list(zip(*ensemble))
    fit_constants = []
    for i in range(6):
        print('Distribution for', constant_name[i])
        c = fit_gauss_curve(distributed_parms[i])
        fit_constants.append(c)
        print()
    return fit_constants


def replace_cell(fn, const_values):
    """ Write a new cell file based on the provided one, containing the new
        constants as defined by fitting.
    """
    const_names = ['a', 'b', 'c', 'al', 'be', 'ga']
    cell_dict = {}
    for i in range(6):
        cell_dict[const_names[i]] = const_values[i]
    lines = []
    # read existing cell file
    with open(fn, 'r') as f_in:
        for ln in f_in:
            lines.append(ln)
    # write new cell file
    with open(f'{fn}_refined', 'w') as f_out:
        for ln in lines:
            items = ln.split()
            if len(items) >= 3 and items[0] in const_names:
                items[2] = '{:.2f}'.format(cell_dict[items[0]])
                new_ln = ' '.join(items)
                f_out.write(new_ln + '\n')
            else:
                f_out.write(ln)
