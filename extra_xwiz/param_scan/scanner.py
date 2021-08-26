import os.path as osp
import logging
import subprocess
import time
from os import getcwd, makedirs, chdir
from typing import Any, Union

import numpy as np
import toml
import xarray as xr

from . import scan_output as sout
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
        Scan parameter value from the parameters scanner config - either
        a list or a dictionary with 'start', 'stop', and 'step' keys.

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
        settings = self.scan_conf['settings']

        if xwiz_conf_file is not None:
            if ('xwiz_config' in settings
                and xwiz_conf_file != settings['xwiz_config']):
                log.warning(
                    "Ignoring xwiz_config in the parameters scanner settings.")
            xwiz_conf_sel = xwiz_conf_file
        else:
            xwiz_conf_sel = settings['xwiz_config']
        self.xwiz_conf = toml.load(xwiz_conf_sel)

        self.scan_dir = getcwd()
        self.xwiz_dir = osp.abspath(osp.dirname(xwiz_conf_sel))

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

        # Total number of jobs
        self._n_jobs = 1
        for _, n_items in self.scan_items:
            self._n_jobs *= n_items
        # Currently runing job id:
        self._cur_job = 0
        # Log when % of jobs finished
        if 'log_completion' in settings:
            self.log_completion = settings['log_completion']
        else:
            self.log_completion = 30


    def _iterate_folders(
        self, folder_base, iter_pars, run_method, make_folders=False,
        folder_vals_all={}, scan_coords=[], **kwargs
    ):
        sub_pars = iter_pars[:]
        param, n_iter = sub_pars.pop(0)

        for i_iter in range(n_iter):
            folder_path = folder_base + osp.sep + f"{param}_{i_iter:02d}"
            folder_toml = folder_path + osp.sep + "folder_value.toml"
            folder_vals = dict()
            for key in self.scan_conf['scan'][param].keys():
                param_vals = get_scan_val(self.scan_conf['scan'][param][key])
                folder_vals[key] = param_vals[i_iter]
                if key in folder_vals_all:
                    raise RuntimeError(
                        f"Folder value for {key} specified multiple times.")
            folder_vals_cur = folder_vals_all.copy()
            folder_vals_cur.update(folder_vals)
            scan_coords_cur = scan_coords.copy()
            scan_coords_cur.append(i_iter)

            if (osp.exists(folder_path)):
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
                self._iterate_folders(
                    folder_path, sub_pars, run_method, make_folders,
                    folder_vals_cur, scan_coords_cur, **kwargs
                )
            else:
                run_method(
                    folder_path, folder_vals_cur, scan_coords_cur, **kwargs
                )


    def _prep_folder(self, folder, folder_vals, scan_coords, link_paths):
        for link_src, link_dst in link_paths:
            link_dst_full = osp.abspath(folder + osp.sep + link_dst)
            if not osp.exists(link_dst_full):
                utl.make_link(link_src, link_dst_full)

        xwiz_folder_conf = self.xwiz_conf.copy()
        for parameter, value in folder_vals.items():
            set_dict_val(xwiz_folder_conf, parameter, value)
        with open(folder + osp.sep + "xwiz_conf.toml", 'w') as conf_file:
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
                if not osp.isabs(path_val):
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
            tmp_path = self.xwiz_dir + osp.sep + path
            abs_path = osp.abspath(osp.realpath(tmp_path))
            if osp.exists(abs_path):
                link_paths.append((abs_path, path))
            else:
                log.warning(
                    f"Relative path from xwiz config does not exist:"
                    f" {path_par} = {path}")

        self._iterate_folders(
            self.scan_dir, self.scan_items, self._prep_folder, True,
            link_paths=link_paths)


    def _run_folder(self, folder, folder_vals, scan_coords, log_nth):
        folder_name = folder[len(self.scan_dir)+1:]
        def print_progress(n_cur, n_tot, folder):
            return f"{n_cur}/{n_tot} Running in: {folder}"

        if self._get_folder_output(folder) is None:
            chdir(folder)
            with open('run_folder.log', 'w') as flog:
                proc = subprocess.Popen(
                    ['xwiz-workflow', '-a', '-d'],
                    stdout=flog, stderr=flog
                )
            while proc.poll() is None:
                utl.print_progress_bar(
                    self._cur_job, self._n_jobs,
                    extra_string=print_progress, folder=folder_name
                )
                time.sleep(0.2)
            chdir(self.scan_dir)

        self._cur_job += 1
        if (self._cur_job % log_nth == 0
            or self._cur_job >= self._n_jobs
            ):
            log.info(f"Finished job {self._cur_job}/{self._n_jobs}: {folder}.")
        if self._cur_job >= self._n_jobs:
            utl.print_progress_bar(self._cur_job, self._n_jobs)
            print()


    def run_jobs(self):
        self._cur_job = 0
        log_nth_job = int(self._n_jobs*self.log_completion/100 + 0.999)
        self._iterate_folders(
            self.scan_dir, self.scan_items, self._run_folder,
            log_nth=log_nth_job
        )


    def _get_folder_output(self, folder):
        xwiz_pref = self.xwiz_conf['data']['list_prefix']
        summ_file = folder + osp.sep + f"{xwiz_pref}.summary"
        if (osp.exists(summ_file)):
            return sout.get_xwiz_index_rate(summ_file)
        else:
            return None


    def _output_folder(self, folder, folder_vals, scan_coords, output_array):
        index_rate = self._get_folder_output(folder)
        output_array[tuple(scan_coords)] = index_rate


    def collect_outputs(self):
        # Prepare xarray to store output
        scan_shape = list()
        scan_dims = list()
        scan_coords = dict()
        for param, n_vals in self.scan_items:
            scan_shape.append(n_vals)
            scan_dims.append(param)
            for key in self.scan_conf['scan'][param].keys():
                if param.lower() in key.lower():
                    param_coords = get_scan_val(self.scan_conf['scan'][param][key])
                    scan_coords[param] = param_coords
                    break
        empty_arr = np.empty(scan_shape)
        empty_arr[:] = np.NaN
        scan_data = xr.DataArray(empty_arr, dims=scan_dims, coords=scan_coords)
        scan_data.attrs["long_name"] = "indexing rate"
        scan_data.attrs["units"] = "%"

        self._iterate_folders(
            self.scan_dir, self.scan_items, self._output_folder,
            output_array=scan_data
        )

        for out_key in self.scan_conf['output'].keys():
            if out_key in sout.output_processors.dict:
                processor = sout.output_processors.dict[out_key]
                processor(scan_data, **self.scan_conf['output'][out_key])
            else:
                log.error(f"Unrecognized output processor: {out_key}.")
