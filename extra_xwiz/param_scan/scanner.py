import os.path
import logging
import toml
from os import getcwd, makedirs
from typing import Any, Union

from .. import utilities as utl


log = logging.getLogger(__name__)

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
    """Get a list of scan parameter values for iteration.

    Parameters
    ----------
    par_val : Union[list, dict]
        Scan parameter value from the parameters scanner config. Either a list
        or a dictionary with 'start', 'stop', and 'step' keys.

    Returns
    -------
    list
        List of parameter values for iteration.
    """
    if isinstance(par_val, dict):
        if 'start' not in par_val:
            par_val['start'] = 0
        if 'step' not in par_val:
            par_val['step'] = 1
        return list(range(par_val['start'], par_val['end']+1, par_val['step']))
    else:
        return par_val


class ParameterScanner:

    def __init__(self, scan_conf_file, xwiz_conf_file=None):
        self.scan_conf = toml.load(scan_conf_file)

        if xwiz_conf_file is not None:
            if ('conf_file' in self.scan_conf['xwiz']
                and xwiz_conf_file != self.scan_conf['xwiz']['conf_file']):
                log.warning(
                    "Ignoring conf_file in the parameters scanner config.")
            xwiz_conf_sel = xwiz_conf_file
        else:
            xwiz_conf_sel = self.scan_conf['xwiz']['conf_file']
        self.xwiz_conf = toml.load(xwiz_conf_sel)

        self.scan_dir = getcwd()
        self.xwiz_dir = os.path.abspath(os.path.dirname(xwiz_conf_sel))

        self.scan_items = list()
        parameters = sorted(self.scan_conf['scan'].keys(), key=str.lower)
        for param in parameters:
            n_iter = len(next(iter(self.scan_conf['scan'][param].values())))
            # All parameters in the scan have to have the same number of items
            for key in self.scan_conf['scan'][param].keys():
                if len(self.scan_conf['scan'][param][key]) != n_iter:
                    raise RuntimeError(
                        f"Incompatible number of items in 'scan.{param}'.")
            self.scan_items.append((param, n_iter))


    def iterate_folders(
        self, folder_base, iter_pars, run_method, make_folders=False,
        folder_vals_all={}, *args, **kwargs
    ):
        sub_pars = iter_pars[:]
        param, n_iter = sub_pars.pop(0)

        for i_iter in range(n_iter):
            folder_path = folder_base + os.path.sep + f"{param}_{i_iter:02d}"
            folder_toml = folder_path + os.path.sep + "value.toml"
            folder_vals = dict()
            for key in self.scan_conf['scan'][param].keys():
                param_vals = get_scan_val(self.scan_conf['scan'][param][key])
                folder_vals[key] = param_vals[i_iter]
                if key in folder_vals_all:
                    raise RuntimeError(
                        f"Folder value for {key} specified multiple times.")
            folder_vals_cur = folder_vals_all.copy()
            folder_vals_cur.update(folder_vals)

            if (os.path.exists(folder_path)):
                if toml.load(folder_toml) != folder_vals:
                    raise RuntimeError(
                        f"Folder '{folder_path}' exists but folder value is"
                        f"incompatible to {folder_vals}.")
            else:
                if make_folders:
                    makedirs(folder_path)
                    with open(folder_toml, 'w') as toml_file:
                        toml.dump(folder_vals, toml_file)
                else:
                    raise RuntimeError(
                        f"Folder '{folder_path}' does not exist.")

            if sub_pars:
                self.iterate_folders(
                    folder_path, sub_pars, run_method, make_folders,
                    folder_vals_cur, *args, **kwargs
                )
            else:
                run_method(folder_path, folder_vals_cur, *args, **kwargs)


    def prep_folder(self, folder, folder_vals, link_paths):
        for link_src, link_dst in link_paths:
            link_dst_full = os.path.abspath(folder + os.path.sep + link_dst)
            if not os.path.exists(link_dst_full):
                utl.make_link(link_src, link_dst_full)

        xwiz_folder_conf = self.xwiz_conf.copy()
        for parameter, value in folder_vals.items():
            set_dict_val(xwiz_folder_conf, parameter, value)
        with open(folder + os.path.sep + "xwiz_conf.toml", 'w') as conf_file:
            toml.dump(xwiz_folder_conf, conf_file)


    def make_folders(self):
        # List of the relative paths in xwiz config
        relative_paths = list()
        def update_relative_paths(path_par, path_val):
            if isinstance(path_val, str) and ',' in path_val:
                path_val = [st.strip() for st in path_val.split(',')]
            if isinstance(path_val, list):
                for path in path_val:
                    update_relative_paths(path_par, path)
            else:
                if not os.path.isabs(path_val):
                    relative_paths.append((path_par, path_val))

        for path_par in self.scan_conf['xwiz']['path_parameters']:
            try:
                path_val = get_dict_val(self.xwiz_conf, path_par)
            except KeyError:
                log.warning(f"No '{path_par}' parameter in xwiz config.")
            else:
                update_relative_paths(path_par, path_val)

        # List relative paths which can be linked
        link_paths = list()
        for path_par, path in relative_paths:
            tmp_path = self.xwiz_dir + os.path.sep + path
            abs_path = os.path.abspath(os.path.realpath(tmp_path))
            if os.path.exists(abs_path):
                link_paths.append((abs_path, path))
            else:
                log.warning(
                    f"Relative path from xwiz config does not exist:"
                    f" {path_par} = {path}")

        self.iterate_folders(
            self.scan_dir, self.scan_items, self.prep_folder, True,
            link_paths=link_paths)


    def run_folder(self, folder, folder_vals, link_paths):
        pass

    def run_jobs(self):
        # Total number of jobs
        n_jobs = 1
        for _, n_items in self.scan_items:
            n_jobs *= n_items


    def collect_output(self):
        pass
