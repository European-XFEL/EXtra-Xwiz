import logging
import os.path as osp
import subprocess
import time
from os import getcwd, makedirs, chdir
from typing import Callable

import numpy as np
import pandas as pd
import toml
import xarray as xr

from . import output as sout
from . import utilities as sutl
from .. import utilities as utl

log = logging.getLogger(__name__)


class ParameterScanner:
    """Class to perform a grid scan over selected xwiz parameters and
    collect xwiz job results.

    Parameters
    ----------
    scan_conf_file : str
        Path to the parameters scan configuration file.
    xwiz_conf_file : str, optional
        Path to the xwiz configuration file, by default None
    replace : bool, optional
        Whether to replace existing scan folders, by default False.

    Raises
    ------
    RuntimeError
        In case any of the scans in scan config has parameters with
        different number of items.
    """

    def __init__(
        self, scan_conf_file: str, xwiz_conf_file: str = None,
        replace: bool = False
    ):
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
        log.info(f"Running with xwiz config from: {xwiz_conf_sel}")
        self.xwiz_conf = toml.load(xwiz_conf_sel)

        self.replace = replace
        self.scan_dir = getcwd()
        self.xwiz_dir = osp.abspath(osp.dirname(xwiz_conf_sel))

        self.scan_items = list()
        parameters = sorted(self.scan_conf['scan'].keys(), key=str.lower)
        for param in parameters:
            param_rand_values = sutl.get_scan_val(
                next(iter(self.scan_conf['scan'][param].values())))
            n_iter = len(param_rand_values)
            # All parameters in the scan have to have the same number of items
            for key in self.scan_conf['scan'][param].keys():
                param_key_values = sutl.get_scan_val(
                    self.scan_conf['scan'][param][key])
                if len(param_key_values) != n_iter:
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
        self, iter_pars: tuple, folder_base: str, run_method: Callable,
        make_folders: bool = False, folder_vals_prev: dict = None,
        scan_coords: list = None, **kwargs
    ) -> None:
        """Iterate through the scan folders and run specified method in
        each of them.

        Parameters
        ----------
        iter_pars : tuple[str, int]
            Tuple with scan parameter names and number of iterations for
                each of them.
        folder_base : str
            Folder path for current iteration step.
        run_method : Callable[str, dict, tuple, **kwargs]
            A method which should be executed at each end directory of
            the scan. It has to accept next paramters in order:
                folder: str
                    Folder path for current scan step.
                folder_vals: dict
                    Dictionary with {parameter:value} for all parameters
                    which need to be modified in the xwiz config.
                scan_coords: list
                    List of integer indices for the current scan step.
                **kwargs:
                    Any additional keyword parameters.
        make_folders : bool, optional
            Whether to make an iteration folder if it does not exist,
            by default False.
        folder_vals_prev : dict, optional
            Dictionary of folder values ({parameter:value} pairs for
            all parameters which need to be modified in the xwiz config)
            for the parent folder, by default {}.
        scan_coords : list, optional
            List of integer indices for the scan step of the parent
            folder, by default [].
        """
        if folder_vals_prev is None:
            folder_vals_prev = dict()
        if scan_coords is None:
            scan_coords = list()

        sub_pars = iter_pars[:]
        param, n_iter = sub_pars.pop(0)

        for i_iter in range(n_iter):
            folder_vals = sutl.get_folder_values(
                i_iter, self.scan_conf['scan'][param], folder_vals_prev)
            folder_vals_cur = folder_vals_prev.copy()
            folder_vals_cur.update(folder_vals)
            scan_coords_cur = scan_coords.copy()
            scan_coords_cur.append(i_iter)

            folder_path = folder_base + osp.sep + f"{param}_{i_iter:02d}"
            sutl.check_scan_folder(
                folder_path, folder_vals, make_folders, self.replace)

            if sub_pars:
                self._iterate_folders(
                    sub_pars, folder_path, run_method, make_folders,
                    folder_vals_cur, scan_coords_cur, **kwargs
                )
            else:
                run_method(
                    folder_path, folder_vals_cur, scan_coords_cur, **kwargs
                )

    def _prep_folder(
        self, folder: str, folder_vals: dict, scan_coords: list,
        link_paths: list
    ) -> None:
        """Prepare xwiz configuration file and symbolic links required
        for running xwiz job in one of the scan folders.

        Parameters
        ----------
        folder : str
            Path to the scan folder.
        folder_vals : dict
            Dictionary with {parameter:value} for all parameters which
            need to be modified in the xwiz config.
        scan_coords : list
            List of integer indices for the current scan step.
            Not used by this method.
        link_paths : list
            List of tuples (link_src, link_dst) with source and
            destination paths for the symbolic links required by the
            xwiz job.
        """
        for link_src, link_dst in link_paths:
            link_dst_full = osp.abspath(folder + osp.sep + link_dst)
            if not osp.exists(link_dst_full):
                utl.make_link(link_src, link_dst_full)

        xwiz_folder_conf = self.xwiz_conf.copy()
        for parameter, value in folder_vals.items():
            utl.set_dotdict_val(xwiz_folder_conf, parameter, value)
        with open(folder + osp.sep + "xwiz_conf.toml", 'w') as conf_file:
            toml.dump(xwiz_folder_conf, conf_file)

    def make_folders(self) -> None:
        """Prepare all scan folders for running xwiz jobs."""
        # List of the relative paths in xwiz config
        relative_paths = list()
        for path_par in self.scan_conf['xwiz']['path_parameters']:
            try:
                path_val = utl.get_dotdict_val(self.xwiz_conf, path_par)
            except KeyError:
                log.warning(f"No '{path_par}' parameter in xwiz config.")
            else:
                sutl.append_relative_paths(path_par, path_val, relative_paths)

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
            self.scan_items, self.scan_dir, self._prep_folder, True,
            link_paths=link_paths)

    def _run_folder(
        self, folder: str, folder_vals: dict, scan_coords: list, log_nth: int
    ) -> None:
        """Run xwiz-workflow in one of the scan folders.

        Parameters
        ----------
        folder : str
            Path to the scan folder.
        folder_vals : dict
            Dictionary with {parameter:value} for all parameters which
            have been modified in the xwiz config.
            Not used by this method.
        scan_coords : list
            List of integer indices for the current scan step.
            Not used by this method.
        log_nth : int
            After finishing execution of every log_nth job write a
            message to the log.
        """
        folder_name = folder[len(self.scan_dir)+1:]

        def print_progress(n_cur, n_tot, folder):
            return f"{n_cur}/{n_tot} Running in: {folder}"

        # If folder foms cannot be read - the job needs to be executed
        if not self._get_folder_foms(folder):
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
                or self._cur_job >= self._n_jobs):
            log.info(f"Finished job {self._cur_job}/{self._n_jobs}: {folder}.")
        if self._cur_job >= self._n_jobs:
            utl.print_progress_bar(self._cur_job, self._n_jobs)
            print()

    def run_jobs(self) -> None:
        """Run xwiz job in all scan folders in which foms cannot be read
        from the summary file."""
        self._cur_job = 0
        log_nth_job = int(self._n_jobs*self.log_completion/100 + 0.999)
        self._iterate_folders(
            self.scan_items, self.scan_dir, self._run_folder,
            log_nth=log_nth_job
        )

    def _get_folder_foms(self, folder: str) -> dict:
        """Get foms from the xwiz summary file in the specified scan
        folder.

        Parameters
        ----------
        folder : str
            Path to the scan folder.

        Returns
        -------
        dict
            Dictionary of foms read from the xwiz summary file.
        """
        folder_conf_file = folder + osp.sep + "xwiz_conf.toml"
        folder_config = toml.load(folder_conf_file)
        xwiz_pref = folder_config['data']['list_prefix']
        summ_file = folder + osp.sep + f"{xwiz_pref}.summary"
        return sout.get_xwiz_foms(summ_file)

    def _output_folder(
        self, folder: str, folder_vals: dict, scan_coords: list,
        output_dataset: xr.Dataset
    ) -> None:
        """Collect output from one of the scan folders.

        Parameters
        ----------
        folder : str
            Path to the scan folder.
        folder_vals : dict
            Dictionary with {parameter:value} for all parameters which
            have been modified in the xwiz config.
            Not used by this method.
        scan_coords : list
            List of integer indices for the current scan step.
        output_dataset : xr.Dataset
            Dataset to store resulting foms.
        """
        xwiz_foms = self._get_folder_foms(folder)
        for fom in xwiz_foms:
            output_dataset[fom][tuple(scan_coords)] = xwiz_foms[fom]

    def collect_outputs(self) -> None:
        """Read foms from the summary files in all scan folders."""
        # Prepare xarray Dataset to store output
        scan_shape = list()
        scan_dims = list()
        scan_coords = dict()
        for param, n_vals in self.scan_items:
            scan_shape.append(n_vals)
            scan_dims.append(param)
            for key in self.scan_conf['scan'][param].keys():
                if param.lower() in key.lower():
                    param_coords = sutl.get_scan_val(
                        self.scan_conf['scan'][param][key])
                    scan_coords[param] = param_coords
                    break
        empty_arr = np.empty(scan_shape)
        empty_arr[:] = np.NaN
        scan_data = xr.Dataset()
        for fom in sout.FOMS:
            data_arr = xr.DataArray(
                empty_arr.copy(), dims=scan_dims, coords=scan_coords)
            data_arr.attrs["long_name"] = fom
            scan_data.update({fom: data_arr.astype(sout.FOMS[fom]['type'])})

        self._iterate_folders(
            self.scan_items, self.scan_dir, self._output_folder,
            output_dataset=scan_data
        )

        pd.set_option('display.max_columns', None)
        pd.set_option('display.expand_frame_repr', False)
        log.info(f"Parameters scan results:\n{scan_data.to_dataframe()}")

        for out_key in self.scan_conf['output'].keys():
            if out_key in sout.output_processors.dict:
                processor = sout.output_processors.dict[out_key]
                processor(scan_data, **self.scan_conf['output'][out_key])
            else:
                log.error(f"Unrecognized output processor: {out_key}.")
