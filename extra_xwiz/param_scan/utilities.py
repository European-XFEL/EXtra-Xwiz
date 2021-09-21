import os.path as osp
from typing import Union
from os import makedirs
from shutil import rmtree

import toml


def get_scan_val(par_val: Union[list, dict]) -> list:
    """Get a list of scan parameter values.

    Parameters
    ----------
    par_val : Union[list, dict]
        Scan parameter value from the parameters scanner config - either
        a list or a dictionary with 'start', 'stop', and 'step' keys.

    Returns
    -------
    list
        A list of parameter values to iterate over.
    """
    if isinstance(par_val, dict):
        if 'start' not in par_val:
            par_val['start'] = 0
        if 'step' not in par_val:
            par_val['step'] = 1
        return list(range(par_val['start'], par_val['end']+1, par_val['step']))
    elif not isinstance(par_val, list):
        return [par_val]
    else:
        return par_val


def get_folder_values(
    i_iter: int, scan_param_dict: dict, folder_vals_prev: dict
) -> dict:
    """Get folder values from scan_param_dict for iteration i_iter.

    Parameters
    ----------
    i_iter : int
        Number of parameter scan iteration for current folder.
    scan_param_dict : dict
        A dictionary with scan parameters.
    folder_vals_prev : dict
        Folder values specified in parent folders.

    Returns
    -------
    dict
        A dictionary with dot-separated xwiz scan parameters as keys and
        values for iteration i_iter.

    Raises
    ------
    RuntimeError
        Value for the folder value key have already been specified in
        one of the parent directories.
    """
    folder_vals = dict()
    for key in scan_param_dict.keys():
        param_vals = get_scan_val(scan_param_dict[key])
        folder_vals[key] = param_vals[i_iter]
        if key in folder_vals_prev:
            raise RuntimeError(
                f"Folder value for {key} specified multiple times.")
    return folder_vals


def check_scan_folder(
    folder_path: str, folder_vals: dict, make_folder: bool,
    replace_folder: bool
) -> None:
    """Check or create a folder for one of the parameters scan steps.

    Parameters
    ----------
    folder_path : str
        Path to the current scan folder.
    folder_vals : dict
        Dictionary of xwiz config parameters which correspond to the
        current scan folder.
    make_folder : bool
        Whether to create a folder if it does no exist or rise an error.
    replace_folder : bool
        Whether to replace an already existing folder.

    Raises
    ------
    RuntimeError
        If a scan folder exists and should not be replaced but folder
        values do not correspond to folder_vals.
    RuntimeError
        If a scan folder should exist but it does not.
    """
    folder_toml = folder_path + osp.sep + "folder_value.toml"

    if (make_folder and replace_folder and osp.exists(folder_path)):
        rmtree(folder_path)

    if osp.exists(folder_path):
        if toml.load(folder_toml) != folder_vals:
            raise RuntimeError(
                f"Folder '{folder_path}' exists but folder value is"
                f"incompatible to {folder_vals}.")
    else:
        if make_folder:
            makedirs(folder_path)
            with open(folder_toml, 'w') as toml_file:
                toml.dump(folder_vals, toml_file)
        else:
            raise RuntimeError(
                f"Folder '{folder_path}' does not exist.")


def append_relative_paths(
    path_par: str, path_val: Union[str, list], relative_paths: list
) -> None:
    """If xwiz path parameter is a relative path - append it to the
    relative_paths.

    Parameters
    ----------
    path_par : str
        Dot-separated xwiz path parameter.
    path_val : Union[str, list]
        Value of the path parameter as a string (paths could be comma
        separated) or a list of strings.
    relative_paths : list
        A list of tuples (path_par, path_val) for the relative paths.
    """
    if isinstance(path_val, str) and ',' in path_val:
        path_val = [st.strip() for st in path_val.split(',')]
    if isinstance(path_val, list):
        for path in path_val:
            append_relative_paths(path_par, path, relative_paths)
    else:
        if not osp.isabs(path_val):
            relative_paths.append((path_par, path_val))
