import os.path as osp
from typing import Any, Union

def get_dict_val(dictionary: dict, parameter: str) -> Any:
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
        return get_dict_val(dictionary[key], new_parameter)
    else:
        return dictionary[parameter]

def set_dict_val(dictionary: dict, parameter: str, value: Any) -> None:
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
        set_dict_val(dictionary[key], new_parameter, value)
    else:
        dictionary[parameter] = value

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

def _get_folder_values(
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
    # scan_param_dict => self.scan_conf['scan'][param]
    for key in scan_param_dict.keys():
        param_vals = get_scan_val(scan_param_dict[key])
        folder_vals[key] = param_vals[i_iter]
        if key in folder_vals_prev:
            raise RuntimeError(
                f"Folder value for {key} specified multiple times.")
    return folder_vals

def append_relative_paths(
    path_par: str, path_val: Union[str, list], relative_paths: list
):
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
