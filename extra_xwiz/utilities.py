"""Utilities"""

from ast import Pass
from collections.abc import Iterable
from copy import deepcopy
from functools import wraps
from getpass import getuser
from glob import glob
import json
import psutil
import re
import shutil
import subprocess
import os, re, time
from typing import Any, Type, Tuple, Collection, Callable
import warnings

import h5py
import numpy as np
from scipy.optimize import curve_fit
import toml

# Local imports
from . import crystfel_info as cri


DEFAULT_RANGE = {'start': 0, 'end': -1, 'step': 1}


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


def print_progress_bar(
    n_current, n_total, length=50, fill='#',
    extra_string=lambda s1, s2: '', **kwargs
):
    state_str = "—\/"
    state = getattr(print_progress_bar, 'state', -1)
    state = state + 1 if state < (len(state_str) - 1) else 0
    state_ch = state_str[state]
    print_progress_bar.state = state

    frac = n_current / n_total
    progress = f"{100 * frac:.1f}%"
    filled_len = int(length * frac)
    if filled_len < length:
        bar = fill * filled_len + state_ch + '—' * (length - filled_len - 1)
    else:
        bar = fill * filled_len

    extra_str = extra_string(n_current, n_total, **kwargs)
    print("\x1b[2K", end='\r')
    print(f" [{bar}] {progress} {extra_str}", end='\r')


def print_simple_bar(n_current, n_total, length=80, fill='#'):
    """ Visualize a percent fraction by a bar, update in-line using <CR> char.
    """
    progress = '{0:.1f}'.format(100 * (n_current / float(n_total)))
    filled_len = int(length * n_current // n_total)
    bar = fill * filled_len + '-' * (length - filled_len)
    print('\r |%s| %s%%' % (bar, progress), end='\r')


def print_crystfel_bar(n_current, n_total, n_crystals, length=80, fill='#'):
    """ Like the simple bar, but with crystal number information
    """
    progress = '{0:.1f}'.format(100 * (n_current / float(n_total)))
    filled_len = int(length * n_current // n_total)
    bar = fill * filled_len + '-' * (length - filled_len)
    try:
        index_rate = 100 * n_crystals / float(n_current)
    except ZeroDivisionError:
        index_rate = 0.0
    print('\r |%s| %s%%, ◆ %d, Indexing rate: %.1f%%' % (bar, progress,
          n_crystals, index_rate), end='\r')

def calc_progress(out_logs, n_total, crystfel_version):
    """ Compare total number of processed frames (from logs) at a given time
        to the overall total number of frames to process.
        In addition collect number of found crystals for display.
    """
    n_frames = []
    n_crystals = []
    for log in out_logs:
        # extract numbers of frames processed
        frames_pattern = cri.crystfel_info[crystfel_version] \
                                          ['log_frames_pattern']
        frame_info = re.findall(frames_pattern, open(log).read(), re.M)
        if len(frame_info) == 0:
            current_n_frames = 0
        else:
            current_n_frames = int(frame_info[-1][1])
        n_frames.append(current_n_frames)
        # extract numbers of crystals found
        crystal_pattern = cri.crystfel_info[crystfel_version] \
                                           ['log_crystals_pattern']
        crystal_info = re.findall(crystal_pattern, open(log).read(), re.M)
        if len(crystal_info) == 0:
            current_n_crystals = 0
        else:
            current_n_crystals = int(crystal_info[-1][1])
        n_crystals.append(current_n_crystals)

    n_frames_total = 0
    n_crystals_total = 0
    if len(n_frames) > 0:
        n_frames_total = sum(n_frames)
        n_crystals_total = sum(n_crystals)
    # Update progress bar
    print_crystfel_bar(n_frames_total, n_total, n_crystals_total, length=50)

    return n_frames_total


def wait_or_cancel(
    job_id: str, job_dir: str, n_total: int, crystfel_version: str,
    silent: bool, is_local:bool
) -> int:
    """Monitor slurm jobs and prepare progress bar.

    Parameters
    ----------
    job_id : str
        Id of the slurm job-array / local process.
    job_dir : str
        Slurm processing folder.
    n_total : int
        Total number of frames to be processed.
    crystfel_version : str
        Version of CrystFEL in use.
    silent : bool
        Whether to skip updating the progress bar.
    is_local : bool
        Whether indexamajig is running in local.

    Returns
    -------
    int
        Total number of processed frames.
    """
    if is_local:
        job_type = 'local process'
        logs_name = 'local_0.out'
    else:
        job_type = 'job-array'
        logs_name = f'slurm-{job_id}_*.out'
    print(f' Waiting for the {job_type} {job_id}')
    while True:
        if is_local:
            if not psutil.pid_exists(int(job_id)):
                break
        else:
            queue = subprocess.check_output(['squeue', '-u', getuser()])
            tasks = [x for x in queue.decode('utf-8').split('\n') if job_id in x]
            if len(tasks) == 0:
                break

        out_logs = glob(f'{job_dir}/{logs_name}')
        if not silent:
            n_proc = calc_progress(out_logs, n_total, crystfel_version)
            if n_proc == n_total:
                break

        time.sleep(1)
    # To ensure all frames have been processed
    out_logs = glob(f'{job_dir}/{logs_name}')
    n_proc = calc_progress(out_logs, n_total, crystfel_version)
    print()
    if n_proc < n_total:
        warnings.warn(
            f"Not all frames were processed by slurm: {n_proc}/{n_total}.")
    return n_proc


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
    fn_refined = get_refined_cell_name(fn)
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
        with open(fn_refined, 'w') as f_out:
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
        with open(fn_refined, 'w') as f_out:
            new_cryst = 'CRYST1'
            new_cryst += ''.join([f'{v:9.3f}' for v in const_values[:3]])
            new_cryst += ''.join([f'{v:7.2f}' for v in const_values[3:6]])
            new_cryst += f' {geom}'
            f_out.write(new_cryst)
    else:
        warnings.warn(' Cell file is of unknown type (by extension)!')
    return fn_refined


def cell_as_string(cell_file):
    """Extract unit cell parameters of currently used file to one-line string
    """
    if len(cell_file) < 20:
        cell_string = f"{cell_file:20}"
    else:
        cell_string = f"{cell_file}\n{'':20}"
    if cell_file[-5:] == '.cell':
        cell_info = re.findall(r'( = )([^\s]+)', open(cell_file).read())
        cell_string += '  '.join([item[1] for item in cell_info]) + '\n'
    elif cell_file[-4:] == '.pdb':
        cell_info = open(cell_file).read().splitlines()[0].split()[1:]
        cell_string += '  '.join(cell_info[6:]) + '  ' + '  '.join(cell_info[:6])
    else:
        warnings.warn(' Cell file is of unknown type (by extension)!')
    return cell_string


def get_refined_cell_name(cell_file):
        """Generate a name for the rifened cell parameters file from the
        original cell_file."""
        orig_file = os.path.split(cell_file)[1]
        f_name, f_ext = orig_file.rsplit('.', 1)
        return f"{f_name}_refined.{f_ext}"


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


def get_copy_hdf5_fields(cxi_file):
    """Prepare '--copy-hdf5-field' option parameters for CrystFEL jobs

    Args:
        cxi_file (string): path to the input data in CXI format.

    Returns:
        string: '--copy-hdf5-field' options for CrystFEL.
    """
    str_options = ""
    with h5py.File(cxi_file,'r') as h5file:
        id_path = ""
        for path in ['entry_1', 'instrument']:
            if path in h5file.keys():
                id_path = f"/{path}"
        if not id_path:
            warnings.warn(f"No suitable key in the input data: {cxi_file}.")
            return ""
        for id_key in ['trainId', 'pulseId', 'memoryCell']:
            if id_key in h5file[id_path]:
                str_options += f"  --copy-hdf5-field={id_path}/{id_key} \\\n"
    return str_options

def remove_path(path):
    """
    Remove entry if it is a file, symbolic link or directory.

    Args:
        path (string): absolute or relative path to the entry to be removed.

    Raises:
        ValueError: path is not a file, symbolic link or directory.
    """
    if os.path.exists(path):
        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            raise ValueError(
                f"Path '{path}' is not a file, symbolic link or directory.")

def make_link(src, dst, target_is_directory=False):
    """
    Prepare symbolic link to src at dst if dst is a folder or does not
    exist yet.

    Args:
        src (string): path to the entry to be linked.
        dst (string): destination for the symbolic link, directory or
            non-existing path.
        target_is_directory (bool, optional): parameter to os.symlink().
            Defaults to False.

    Raises:
        ValueError: dst exists and is not a folder.
    """
    src_path = os.path.abspath(os.path.realpath(src))
    src_name = os.path.basename(src_path)   # src_path is normalized

    dst_dir = os.path.dirname(dst)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if os.path.isdir(dst):
        os.symlink(
            src_path,
            dst + os.path.sep + src_name,
            target_is_directory=target_is_directory
        )
    elif not os.path.exists(dst):
        os.symlink(
            src_path,
            dst,
            target_is_directory=target_is_directory
        )
    else:
        raise ValueError(
                f"Destination path '{dst}' already exists and "
                f"is not a folder.")

def make_new_dir(path):
    """
    Make an empty directory. If path already exists - remove it beforehand
    and rise a warning.

    Args:
        path (string): relative or absolute path to the directory to be
            created.
    """
    if os.path.exists(path):
        warnings.warn(f'Directory / file {path} already exists - '
                      f'removing it.')
        remove_path(path)
    os.makedirs(path)

def separate_path(path):
    """
    Normalize provided path and divide it to folder and file name.

    Args:
        path (string): path to be separated.

    Returns:
        (norm_path, path_dir, path_file):
            norm_path (string): absolute normalized path.
            path_dir (string): folder part of the normalized path.
            path_file (string): file from the provided path.
    """
    norm_path = os.path.abspath(os.path.realpath(path))
    if (path.endswith(os.path.sep)
        or (os.path.exists(norm_path) and os.path.isdir(norm_path))
        ):
        norm_path += os.path.sep
    path_dir = os.path.dirname(norm_path)
    path_file = os.path.basename(norm_path)

    return norm_path, path_dir, path_file

def copy_file(src, dst):
    """
    Copy file from src to dst, where dst could be a file or folder.
    In case dst folder does not exist - it will be created.

    Args:
        src (string): source file to copy.
        dst (string): destination - file or folder name.
    """
    src_path, _, src_file = separate_path(src)
    dst_path, dst_dir, dst_file = separate_path(dst)

    # Avoid 'shutil.SameFileError' - no need to copy file into itself
    if (src_path == dst_path
        and src_file):
        return

    # Remove dst file if already exists
    if (os.path.exists(dst_path)
        and dst_file):
        warnings.warn(f'File "{dst}" already exists - replacing it.')
    # Prepare the path to dst if not there yet
    elif not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    shutil.copy2(src_path, dst_path)


def get_dotdict_val(dictionary: dict, parameter: str) -> Any:
    """Get value of the dot-separates parameter form the dictionary.

    Parameters
    ----------
    dictionary : dict
        Dictionary to read parameter from.
    parameter : str
        Dot-separated parameter path in the dictionary, e.g.:
        'some.par' corresponds to dictionary['some']['par'].

    Returns
    -------
    Any
        Value of the parameter in the dictionary.
    """
    if '.' in parameter:
        key, new_parameter = parameter.split('.', 1)
        return get_dotdict_val(dictionary[key], new_parameter)
    else:
        return dictionary[parameter]


def set_dotdict_val(dictionary: dict, parameter: str, value: Any) -> None:
    """Set value for the dot-separates parameter in the dictionary.

    Parameters
    ----------
    dictionary : dict
        Dictionary to set parameter in.
    parameter : str
        Dot-separated parameter path in the dictionary, e.g.:
        'some.par' corresponds to dictionary['some']['par'].
    value : Any
        Value to be assigned to the parameter.
    """
    if '.' in parameter:
        key, new_parameter = parameter.split('.', 1)
        if key not in dictionary:
            dictionary[key] = {}
        set_dotdict_val(dictionary[key], new_parameter, value)
    else:
        dictionary[parameter] = value


def into_list(value: Any) -> list:
    """If an input is not a list - embed it into one. Otherwise return
    the original list."""
    if isinstance(value, list):
        return value
    else:
        return [value]


def string_to_list(value: str) -> list:
    """Convert input string representing a list or just comma-separated
    values to the list of strings."""
    result = [val.strip('"\' ') for val in value.strip('][ ').split(',')]
    return result


def dict_list_broadcast(dict_list: list, n_elements:int) -> list:
    """In case 'dict_list' has a single dictionary - broadcast it to
    'n_elements' values."""
    assert isinstance(dict_list, list), "Expecting a list of dictionaries."
    n_dicts = len(dict_list)
    if n_dicts == n_elements:
        return dict_list
    elif n_dicts != 1:
        raise RuntimeError(
            f"Cannot broadcast {n_dicts} dictionaries to {n_elements} values.")
    else:
        dict_list_res = deepcopy(dict_list)
        for _ in range(n_elements - 1):
            dict_list_res.append(dict_list[0].copy())
        return dict_list_res


def dict_list_update_default(dict_list: list, default: dict) -> list:
    """Update a list of dictionaries with the default dictionary values.

    Parameters
    ----------
    dict_list : list
        Input list of dictionaries.
    default : dict
        Dictionary of the default values.

    Returns
    -------
    list
        List of the input dictionaries updated with the default values.
    """
    dict_list_res = []
    for i_dict in range(len(dict_list)):
        dict_list_res.append(default.copy())
        dict_list_res[i_dict].update(dict_list[i_dict])
        # Cross check for unexpected keys
        for key in dict_list[i_dict]:
            if key not in default:
                print(f"Unexpected key: '{key}'. Default: {default.keys()}.")
    return dict_list_res


def user_input_toml(message: str, default: Any) -> Tuple[bool, Any]:
    """Request user input for a toml configuration parameter.

    Parameters
    ----------
    message : str
        Message to be displayed to the user.
    default : Any
        Default value to return in case of the wrong input.

    Returns
    -------
    Tuple[bool, Any]
        bool
            Whether an input from the user have been accepted.
        Any
            An input from the user (or default value in case of the
            wrong input.
    """
    # To display dictionaries and booleans in a style acceptable for toml
    default_str = str(default)
    if '{' in default_str:
        default_str = default_str.replace("': ", "' = ")
        default_str = default_str.replace("'start'", "start")
        default_str = default_str.replace("'end'", "end")
        default_str = default_str.replace("'step'", "step")
    default_str = default_str.replace('False', 'false').replace('True', 'true')

    usr_inp = input(f'{message} [{default_str}] > ').strip()
    if usr_inp == '':
        return False, default

    # Allow user to input single strings without quotation marks
    if ((isinstance(default, str)
        or isinstance(default, list) and isinstance(default[0], str))
        and usr_inp[0] not in "['\""
        ):
        return True, usr_inp

    # Using toml to decode input values
    usr_inp_str = "input = " + usr_inp
    try:
        usr_inp_dict = toml.loads(usr_inp_str)
    except toml.TomlDecodeError:
        warnings.warn(
            f"Value '{usr_inp}' cannot be decoded by toml;"
            f" kept at default.")
        return False, default
    else:
        return True, usr_inp_dict['input']


def user_input_str(
    message: str, default: Any, re_format: str=None
    ) -> Tuple[bool, str]:
    """Request user's input as a string and match it to the provided
    regular expression.

    Parameters
    ----------
    message : str
        Message to be displayed to the user.
    default : Any
        Default value to return in case user does not provide the input
        or it does not match the regular expression.
    re_format : str, optional
        Regular expression to be matched, by default None.

    Returns
    -------
    Tuple[bool, str]
        bool
            Whether an input from the user have been accepted.
        str
            An input from the user in case it satisfies the regular
            expression, otherwise the default value.
    """
    accepted, usr_inp = user_input_type(message, default, str)
    if not accepted:
        return False, default

    if re_format is None or re.match(re_format, usr_inp):
        return True, usr_inp
    else:
        warnings.warn(
            f"Does not satisfy expected format: r'{re_format}'; "
            f"kept at default.")
        return False, default


def user_input_type(
    message: str, default: Any, val_type: Type
    ) -> Tuple[bool, Any]:
    """Request user's input and convert it to the specified type.

    Parameters
    ----------
    message : str
        Message to be displayed to the user.
    default : Any
        Default value to return in case user does not provide the input
        or it cannot be converted to the specified type.
    val_type : Type
        Type of the expected user's input.

    Returns
    -------
    Tuple[bool, Any]
        bool
            Whether an input from the user have been accepted.
        Any
            An input from the user in case it can be converted to the
            specified type, otherwise the default value.
    """
    accepted, usr_inp = user_input_toml(message, default)
    if accepted:
        if isinstance(usr_inp, val_type):
            return True, usr_inp
        else:
            try:
                return True, val_type(usr_inp)
            except ValueError:
                warnings.warn('Wrong input type; kept at default.')
                return False, default
    else:
        return False, default


def user_input_list(
    message: str, default: Any, val_type: Type, n_elements: int=-1,
    broadcastable: bool=False
    ) -> Tuple[bool, list]:
    """Request user's input as a single value or a list of values and
    convert it to the list of values with the specified type.

    Parameters
    ----------
    message : str
        Message to be displayed to the user.
    default : Any
        Default value to return in case user does not provide the input
        or it cannot be converted to the specified type.
    val_type : Type
        Type of the expected user's input.
    n_elements : int, optional
        Expected number of the list elements, by default -1 which means
        any number. Lists with 1 element are accepted in case
        broadcastable is True.
    broadcastable : bool, optional
        Whether a value can be broadcast, by default False.

    Returns
    -------
    bool, list
        bool
            Whether an input from the user have been accepted.
        list
            An input from the user as a list of values of specified
            type, or the default value in case user's input cannot be
            converted.
    """
    accepted, usr_inp = user_input_toml(message, default)
    if accepted:
        usr_inp = into_list(usr_inp)
        n_inp = len(usr_inp)
        if ((n_elements > 0) and (n_inp != n_elements)
            and (not broadcastable or n_inp != 1)):
            warnings.warn(
                f'Expected a list with {n_elements} elements; '
                f'kept at default.'
            )
            return False, default
        try:
            return True, [val_type(val) for val in usr_inp]
        except ValueError:
            warnings.warn('Wrong type; kept at default.')
            return False, default
    else:
        return False, default


def user_input_path(
    message: str, default: str=None
    ) -> Tuple[bool, str]:
    """Request user to provide existing path.

    Parameters
    ----------
    message : str
        Message to be displayed to the user.
    default : str, optional
        Default path to a file or folder, by default None, which will
        keep requesting user's input until an existing path will be
        provided.

    Returns
    -------
    Tuple[bool, str]
        bool
            Whether an input from the user have been accepted.
        str
            An input from the user in case specified path exists,
            otherwise the default value.
    """
    while True:
        accepted, usr_inp = user_input_toml(message, default)
        if accepted and isinstance(usr_inp, str):
            if os.path.exists(usr_inp):
                return True, usr_inp
            elif default is not None:
                warnings.warn('Path does not exist; kept at default.')
                return False, default
            else:
                print(
                    "Path does not exist - please provide an existing path.")
        elif default is not None:
            return False, default
        else:
            print("Please provide an existing path.")


def user_input_choice(
    message: str, default: Any, options: list
    ) -> Tuple[bool, Any]:
    """Request user input and check if it corresponds to one of the
    values in 'options'.

    Parameters
    ----------
    message : str
        Message to be displayed to the user.
    default : Any
        Default value to return in case of the wrong input.
    options : list
        List of the appropriate value options.

    Returns
    -------
    Tuple[bool, Any]
        bool
            Whether an input from the user have been accepted.
        Any
            An input from the user (or default value in case of the
            inappropriate input.
    """
    accepted, usr_inp = user_input_toml(message, default)
    if accepted:
        if usr_inp in options:
            return True, usr_inp
        else:
            warnings.warn(
                f'Input has to be one of {options}; kept at default.')
            return False, default
    else:
        return False, default


def table_weighted_average(
    table: list, col_value: int, col_weight: int
) -> float:
    """Weighted average over the table of values.

    Parameters
    ----------
    table : list
        List of strings with table lines as space separated values.
    col_value : int
        Index of the column with values to average.
    col_weight : int
        Index of the column with weights.
    """
    w_sum = 0.0
    f_sum = 0.0
    for line in table:
        item = line.split()
        w_sum += int(item[col_weight])
        f_sum += (int(item[col_weight]) * float(item[col_value]))
    return (f_sum / w_sum)


def is_value_in_range(value: int, range_dict: dict) -> bool:
    """Check if integer value belongs to the specified range.

    Parameters
    ----------
    value : int
        Integer value to check.
    range_dict : dict
        Range dictionary of the form:
            {'start': 0, 'end': -1, 'step': 1}

    Returns
    -------
    bool
        True if in the specified range.
    """
    if value < range_dict['start']:
        return False
    if range_dict['end'] >= 0 and value > range_dict['end']:
        return False
    div_modulo = (value - range_dict['start']) % range_dict['step']
    if div_modulo == 0:
        return True
    else:
        return False


def ignore_none(comp_func: Callable) -> Callable:
    """Decorator for min/max functions to ignore Nones"""
    @wraps(comp_func)
    def nones_wrapper(*args, **kwargs):
        if len(args) == 1:
            args = tuple(args[0])
        no_none_args = []
        for val in args:
            if val is not None:
                no_none_args.append(val)
        n_no_none_vals = len(no_none_args)
        if n_no_none_vals == 0:
            return None
        elif n_no_none_vals == 1:
            return no_none_args[0]
        else:
            return comp_func(no_none_args, **kwargs)
    return nones_wrapper

nanmax = ignore_none(max)

