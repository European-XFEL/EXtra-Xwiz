"""Utilities"""

from getpass import getuser
from glob import glob
import h5py
import numpy as np
from scipy.optimize import curve_fit
import subprocess
import os, re, time
import warnings


def hex_to_int(hex_str):
    """ Convert to base10 integer (decimal number) from explicit hexadecimal
        input assumption. Will work whether or not string starts with '0x'
    """
    try:
        dec_int = int(hex_str, 16)
    except ValueError:
        warnings.warn(' Illegal string given - cannot be interpreted'
                      ' as hex number. Set to 0xffffffff')
        dec_int = int('ffffffff', 16)  # default for make-virtual-cxi
    print(f' fill-value: {hex_str} = {dec_int}')
    return dec_int


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
    try:
        p, var_matrix = curve_fit(gauss_func, x, y, p0=p0)
        print(p)
    # run-time error may occur upon badly behaved distribution
    except RuntimeError:
        p = list(p0)
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


def print_progress_bar(i, n, n_crystals, length=80, fill='█'):
    """ Visualize a percent fraction by a bar, update in-line using <CR> char.
    """
    percent = '{0:.1f}'.format(100 * (i / float(n)))
    filled_len = int(length * i // n)
    bar = fill * filled_len + '-' * (length - filled_len)
    print('\r Progress: |%s| %s%%. ◆ %d' % (bar, percent, n_crystals),
          end='\r')


def calc_progress(out_logs, n_total):
    """ Compare total number of processed frames (from logs) at a given time
        to the overall total number of frames to process.
        In addition collect number of found crystals for display.
    """
    n_frames = []
    n_crystals = []
    for log in out_logs:
        # extract numbers of frames processed
        frames_pattern = '(\s*\d*.indexable out of |Final:)(\s?\d*\s)(p|i)'
        frame_info = re.findall(frames_pattern, open(log).read(), re.DOTALL)
        if len(frame_info) == 0:
            current_frames = 0
        else:
            current_frames = int(frame_info[-1][1])
        n_frames.append(current_frames)
        # extract numbers of crystals found
        crystal_pattern = '(\),\s*)(\d*)( crystals)'
        crystal_info = re.findall(crystal_pattern, open(log).read(), re.DOTALL)
        if len(crystal_info) == 0:
            current_crystals = 0
        else:
            current_crystals = int(crystal_info[-1][1])
        n_crystals.append(current_crystals)
    # update progress bar unless stdout-logs are not yet available
    if len(n_frames) > 0 and len(n_crystals) > 0:
        print_progress_bar(sum(n_frames), n_total, sum(n_crystals), length=50)


def wait_or_cancel(job_id, n_nodes, n_total, time_limit):
    """ Loop until queue is empty or time-limit reached
    """
    print(' Waiting for job-array', job_id)
    out_logs = []
    # wait until at least one allocated job has passed queueing stage
    while len(out_logs) == 0:
        time.sleep(5)
        out_logs = glob(f'slurm-{job_id}_*.out')
        # This may never happen if array of jobs is submitted. 
        # ARRAY_ID = 0 may be finished before the last ID starts
    max_time = '0:00'
    n_tasks = n_nodes
    # wait until all tasks have finished, hence vanished from the squeue list
    while n_tasks > 0 and seconds(max_time) <= seconds(time_limit):
        queue = subprocess.check_output(['squeue', '-u', getuser()])
        tasks = [x for x in queue.decode('utf-8').split('\n') if job_id in x]
        n_tasks = len(tasks)
        times = [ln.split()[5] for ln in tasks]
        try:
            max_time = max(times)
        except ValueError:
            # if for some reason the list 'times' is empty
            max_time = '0:00'
        calc_progress(out_logs, n_total)
        time.sleep(2)
    # to ensure a full bar after all tasks have finished.
    calc_progress(out_logs, n_total)
    print()


def wait_single(job_id, n_total):
    """ Loop until queue is empty (single non-array SLURM job)
    """
    print(' Waiting for job', job_id)
    out_logs = [f'slurm-{job_id}.out']
    # wait until the one allocated job has passed queueing stage
    while not os.path.exists(f'slurm-{job_id}.out'):
        time.sleep(2)
    n_tasks = 1
    # wait until task has finished, hence vanished from the squeue list
    while n_tasks > 0:
        queue = subprocess.check_output(['squeue', '-u', getuser()])
        tasks = [x for x in queue.decode('utf-8').split('\n') if job_id in x]
        n_tasks = len(tasks)
        calc_progress(out_logs, n_total)
        time.sleep(2)
    # to ensure a full bar after all tasks have finished.
    calc_progress(out_logs, n_total)
    print()


def cell_in_tolerance(probe_constants, reference_file, tolerance):
    """Compare cell constants of one crystal from indexing with expectation
    """
    const_names = ['a', 'b', 'c', 'al', 'be', 'ga']
    reference_value = []
    with open(reference_file, 'r') as f:
        if reference_file[-5:] == '.cell':
            for ln in f:
                if ' = ' not in ln:
                    continue
                if ln.split()[0] in const_names:
                    reference_value.append(float(ln.split()[2]))
        elif reference_file[-4:] == '.pdb':
            for ln in f:
                if ln[:6] == 'CRYST1':
                    reference_value = [float(x) for x in ln.split()[1:7]]
        else:
            warnings.warn(' Cell file is of unknown type')
    for i in range(6):
        if probe_constants[i] < (1 - tolerance) * reference_value[i]:
            return False
        if probe_constants[i] > (1 + tolerance) * reference_value[i]:
            return False
    return True


def get_crystal_frames(stream_file, cell_file, tolerance):
    """ Parse stream file after indexamajig run.
        Check crystals of indexed frames; if they match a prior expectation,
        add event number (frame) and cell constants to respective lists.
    """
    hit_list = []
    cell_ensemble = []

    if cell_file[-5:] == '.cell':
        print(' check against CrystFEL unit-cell format:')
    elif cell_file[-4:] == '.pdb':
        print(' check against PDB/CRYST1 unit-cell format:')
    else:
        warnings.warn(' Unit cell file not recognized by extension!')

    with open(stream_file, 'r') as f:
        for ln in f:
            if 'Image filename:' in ln:
                event_fn = ln.split()[-1]   # path to VDS or Cheetah.h5
            if 'Event:' in ln:
                event_id = ln.split()[-1]   # includes '//'
                event = f'{event_fn} {event_id}'
            if 'Cell parameters' in ln:
                cell_edges = [(10 * float(x)) for x in ln.split()[2:5]]
                cell_angles = [float(x) for x in ln.split()[6:9]]
                cell_constants = cell_edges + cell_angles
                if not cell_in_tolerance(cell_constants, cell_file, tolerance):
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
    if fn[-5:] == '.cell':
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

    elif fn[-4:] == '.pdb':
        with open(fn, 'r') as f_in:
            for ln in f_in:
                if ln[:6] == 'CRYST1':
                    geom = ' '.join(ln.split()[7:])
        with open(f'{fn}_refined', 'w') as f_out:
            new_cryst = 'CRYST1'
            new_cryst += ''.join([f'{v:9.3f}' for v in const_values[:3]])
            new_cryst += ''.join([f'{v:7.2f}' for v in const_values[3:6]])
            new_cryst += f' {geom}'
            f_out.write(new_cryst)
    else:
        warnings.warn(' Cell file is of unknown type (by extension)!')


def cell_as_string(cell_file):
    """Extract unit cell parameters of currently used file to one-line string
    """
    cell_string = '{:20}'.format(cell_file)
    if cell_file[-5:] == '.cell' or cell_file[-13:] == '.cell_refined':
        cell_info = re.findall('( = )([^\s]+)', open(cell_file).read())
        cell_string += '  '.join([item[1] for item in cell_info]) + '\n'
    elif cell_file[-4:] == '.pdb' or cell_file[-12:] == '.pdb_refined':
        cell_info = open(cell_file).read().splitlines()[0].split()[1:]
        cell_string += '  '.join(cell_info[6:]) + '  ' + '  '.join(cell_info[:6])
    else:
        warnings.warn(' Cell file is of unknown type (by extension)!')
    return cell_string


def determine_detector(path):
    """Get a detector type label from file name in run folder
    """
    files = [[], []]
    for i, label in enumerate(['AGIPD', 'JNGFR']):
        files[i] = glob(f'{path}/*{label}*.h5')  
        if len(files[i]) > 0:
            return label
    warnings.warn('NO FILES FOR SUPPORTED DETECTOR TYPES FOUND')
    return ''

def scan_cheetah_proc_dir(path):
    """Get all HDF5 file paths/names of a Cheetah-processed run folder by
       recursion, sample 1% of them for the frame number contained
       :param path:  HDF5 data path given by config
       :return:      total number of files, average frame number as per sample
    """
    file_items = [os.path.join(dp, f) for dp, dn, fn in os.walk(path) for f in fn]
    n_files = len(file_items)
    samples = []
    n_frames = 0
    while len(samples) < (n_files // 100):
        j = np.random.randint(n_files)
        if j not in samples:
            with h5py.File(file_items[j], 'r') as f:
                try:
                    data = f['data/data'][()]
                except KeyError:
                    warnings.warn('The content of your HDF5 data does not seem'
                                  ' to stem from Cheetah based on EuXFEL/'
                                  'AGIPD-1M')
                    exit(0)
            if len(data.shape) != 4 or data.shape[1] != 16:
                warnings.warn('The content of your HDF5 data does not seem to'
                              ' stem from Cheetah based on EuXFEL/AGIPD-1M')
                exit(0)
            n_frames += data.shape[0]
            samples.append(j)
    return n_files, (n_frames / len(samples))
