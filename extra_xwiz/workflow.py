from argparse import ArgumentParser
from collections import OrderedDict
import fileinput
from glob import glob
import h5py
import numpy as np
import os
import shutil
import subprocess
import warnings

from . import config
from . import crystfel_info as cri
from . import geometry as geo
from . import utilities as utl
from .templates import (MAKE_VDS, PROC_VDS_BASH_SLURM, 
                        PROC_CXI_BASH_SLURM, PARTIALATOR_WRAP, CHECK_HKL_WRAP, 
                        COMPARE_HKL_WRAP, CELL_EXPLORER_WRAP, POINT_GROUPS,
                        CONFIG, ADV_CONFIG)
from .summary import (create_new_summary, report_cell_check, report_step_rate,
                      report_total_rate, report_cells, report_merging_metrics,
                      report_reprocess, report_reconfig)

WARN_WRONG_TYPE = 'Wrong type; kept at default.'


class Workflow:

    def __init__(self, home_dir, work_dir, automatic=False, diagnostic=False,
                 reprocess=False, use_peaks=False, use_cheetah=False):
        """Construct a workflow instance from the pre-defined configuration.
           Initialize some class-global 'bookkeeping' variables
        """
        self.home_dir = home_dir
        self.work_dir = work_dir
        self.interactive = not automatic
        self.diagnostic = diagnostic
        self.reprocess = reprocess
        self.use_peaks = use_peaks
        self.use_cheetah = use_cheetah
        self.data_path = ''                        # for special cheetah tree
        self.exp_ids = []
        conf = config.load_from_file()
        data_path = conf['data']['path']
        run_numbers = [int(n) for n in conf['data']['runs'].split(',')]
        self.data_runs = [f'{data_path}/r{run:04d}' for run in run_numbers]
        self.vds_names = conf['data']['vds_names'].split(',')
        if not len(self.vds_names) == len(self.data_runs):
            print('CONFIG ERROR: unequal numbers of VDS files and run-paths')
            exit(0)
        if 'cxi_names' in conf['data']:
            self.cxi_names = conf['data']['cxi_names'].split(',')
        else:
            self.cxi_names = ['']
        if 'n_frames_offset' in conf['data']:
            self.n_frames_offset = conf['data']['n_frames_offset']
        # Check for deprecated parameter
        elif 'frame_offset' in conf['data']:
            warnings.warn(
                "'frame_offset' is being deprecated, please use "
                "'n_frames_offset' instead.")
            self.n_frames_offset = conf['data']['frame_offset']
        else:
            self.n_frames_offset = 0
        if 'n_frames_percent' in conf['data']:
            self.n_frames_percent = conf['data']['n_frames_percent']
        else:
            self.n_frames_percent = 100
        if 'n_frames_max' in conf['data']:
            self.n_frames_max = conf['data']['n_frames_max']
        else:
            self.n_frames_max = -1
        if 'n_frames_total' in conf['data']:
            self.n_frames_total = conf['data']['n_frames_total']
        # Check for deprecated parameter
        elif 'n_frames' in conf['data']:
            warnings.warn(
                "'n_frames' is being deprecated, please use "
                "'n_frames_total' instead.")
            self.n_frames_total = conf['data']['n_frames']
        else:
            self.n_frames_total = -1
        self.list_prefix = conf['data']['list_prefix']

        self._crystfel_version = conf['crystfel']['version']
        if self._crystfel_version not in cri.crystfel_info.keys():
            raise ValueError(f'Unsupported CrystFEL version: '
                             f'{self._crystfel_version}')

        self.geometry = conf['geom']['file_path']
        self.vds_mask = geo.get_bad_pixel(self.geometry)
        self.geom_template = conf['geom']['template_path']
        if ('add_hd5mask' in conf['geom']
            and isinstance(conf['geom']['add_hd5mask'], dict)
            and conf['geom']['add_hd5mask']['run']
            ):
            self.geometry = geo.geom_add_hd5mask(
                self.geometry,
                conf['geom']['add_hd5mask']
            )

        self.n_nodes_all = conf['slurm']['n_nodes_all']
        self.n_nodes_hits = conf['slurm']['n_nodes_hits']
        self.partition = conf['slurm']['partition']
        self.duration_all = conf['slurm']['duration_all']
        self.duration_hits = conf['slurm']['duration_hits']
        self.res_lower = conf['proc_coarse']['resolution']
        self.res_higher = conf['proc_fine']['resolution']
        self.peak_method = conf['proc_coarse']['peak_method']
        self.peak_threshold = conf['proc_coarse']['peak_threshold']
        self.peak_snr = conf['proc_coarse']['peak_snr']
        self.peak_min_px = conf['proc_coarse']['peak_min_px']
        self.peak_max_px = conf['proc_coarse']['peak_max_px']
        self.peaks_path = conf['proc_coarse']['peaks_hdf5_path']
        self.index_method = conf['proc_coarse']['index_method']
        self.local_bg_radius = conf['proc_coarse']['local_bg_radius']
        self.max_res = conf['proc_coarse']['max_res']
        self.min_peaks = conf['proc_coarse']['min_peaks']
        self.indexamajig_extra_options = conf['proc_coarse']['extra_options']

        self.cell_file = conf['unit_cell']['file']
        self.cell_run_refine = conf['unit_cell']['run_refine']
        self.cell_tolerance = conf['frame_filter']['match_tolerance']
        self.integration_radii = conf['proc_fine']['integration_radii']
        self.point_group = conf['merging']['point_group']
        self.scale_model = conf['merging']['scaling_model']
        self.scale_iter = conf['merging']['scaling_iterations']
        self.max_adu = conf['merging']['max_adu']
        self.config = conf      # store the config dictionary to report later
        self.overrides = OrderedDict()    # collect optional config overrides
        self.hit_list = []
        self.cell_ensemble = []
        self.cell_info = []
        self.step = 0

    def crystfel_from_config(self, high_res=2.0):
        """ Inquire the CrystFEL-relevant workflow parameters (provided we are
            in interactive mode)
        """
        cell_keyword = ''

        if self.interactive:
            _resolution = input(f'Processing resolution limit in Å [{high_res}] > ')
            if _resolution != '':
                try:
                    high_res = float(_resolution)
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _peak_method = input(f'Peak-finding method to use [{self.peak_method}] > ')
            if _peak_method != '':
                if _peak_method in ['peakfinder8', 'zaef']:
                    self.peak_method = _peak_method
                    self.overrides['peak_method'] = self.peak_method
                else:
                    warnings.warn('Peak-finding method not known; default kept.')

            _peak_threshold = input(f'Peak threshold [{self.peak_threshold}] > ')
            if _peak_threshold != '':
                try:
                    self.peak_threshold = int(_peak_threshold)
                    self.overrides['peak_threshold'] = self.peak_threshold
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _peak_snr = input(f'Peak min. signal-to-noise [{self.peak_snr}] > ')
            if _peak_snr != '':
                try:
                    self.peak_snr = int(_peak_snr)
                    self.overrides['peak_snr'] = self.peak_snr
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _peak_min_px = input(f'Peak min. pixel count [{self.peak_min_px}] > ')
            if _peak_min_px != '':
                try:
                    self.peak_min_px = int(_peak_min_px)
                    self.overrides['peak_min_px'] = self.peak_min_px
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _index_method = input(f'indexing method to use [{self.index_method}] > ')
            if _index_method != '':
                if _index_method in ['mosflm', 'xds', 'xgandalf']:
                    self.index_method = _index_method
                    self.overrides['index_method'] = self.index_method
                else:
                    warnings.warn('Indexing method not known; default kept.')

            _cell_file = input(f'unit cell file to use as estimate [{self.cell_file}] OR [none] > ')
            if _cell_file != '':
                if _cell_file == 'none':
                    print('Processing without prior unit cell - unknown crystal geometry.')
                self.cell_file = _cell_file

        # check cell file presence; expected 'true' for default or overwrite != 'none'
        if os.path.exists(self.cell_file):
            cell_keyword = f'-p {self.cell_file}'
            self.cell_info.append(utl.cell_as_string(self.cell_file))
            print(' [cell-file check o.k.]')
        elif self.cell_file != 'none':
            warnings.warn('Processing without unit cell due to invalid cell file.')

        return high_res, cell_keyword

    def process_slurm_multi(self, job_dir, high_res, cell_keyword,
                            filtered=False):
        """ Write a batch-script wrapper for indexamajig from the relevant
            configuration parameters and start a process by sbatch submission
        """
        crystfel_import = cri.crystfel_info[self._crystfel_version]['import']
        prefix = f'{self.list_prefix}_hits' if filtered else self.list_prefix
        n_nodes = self.n_nodes_hits if filtered else self.n_nodes_all
        duration = self.duration_hits if filtered else self.duration_all

        # Move list files to the slurm directory
        for input_list in glob(f'{prefix}_*.lst'):
            shutil.move(input_list, job_dir)

        # Make links to the data, geometry and cell files
        if self.use_cheetah:
            # Not sure, needs to be tested
            utl.make_link(
                self.data_path,
                job_dir,
                target_is_directory=True
            )
        else:
            ds_names = self.cxi_names if self.use_peaks else self.vds_names
            for ds_name in ds_names:
                utl.make_link(ds_name, job_dir)

        utl.make_link(self.geometry, job_dir)
        geom_keyword = os.path.basename(self.geometry)

        if cell_keyword != '':
            cell_key_split = cell_keyword.split()
            cell_file = cell_key_split[-1]
            utl.make_link(cell_file, job_dir)
            cell_name = os.path.basename(cell_file)
            cell_keyword = " ".join(cell_key_split[:-1] + [cell_name])

        # Prepare '--copy-hdf5-field' option parameters
        with open(f"{job_dir}/{prefix}_0.lst") as lst_f:
            data_file_0 = lst_f.readline().split(' ')[0]
            copy_fields = utl.get_copy_hdf5_fields(f"{job_dir}/{data_file_0}")

        with open(f'{job_dir}/{prefix}_proc-{self.step}.sh', 'w') as f:
            if self.use_peaks:
                f.write(PROC_CXI_BASH_SLURM % {
                    'IMPORT_CRYSTFEL': crystfel_import,
                    'PREFIX': prefix,
                    'GEOM': geom_keyword,
                    'CRYSTAL': cell_keyword,
                    'CORES': 40,
                    'RESOLUTION': high_res,
                    'PEAKS_HDF5_PATH': self.peaks_path,
                    'INDEX_METHOD': self.index_method,
                    'INT_RADII': self.integration_radii,
                    'COPY_FIELDS': copy_fields,
                    'EXTRA_OPTIONS': self.indexamajig_extra_options
                })
            else:
                f.write(PROC_VDS_BASH_SLURM % {
                    'IMPORT_CRYSTFEL': crystfel_import,
                    'PREFIX': prefix,
                    'GEOM': geom_keyword,
                    'CRYSTAL': cell_keyword,
                    'CORES': 40,
                    'RESOLUTION': high_res,
                    'PEAK_METHOD': self.peak_method,
                    'PEAK_THRESHOLD': self.peak_threshold,
                    'PEAK_MIN_PX': self.peak_min_px,
                    'PEAK_MAX_PX': self.peak_max_px,
                    'PEAK_SNR': self.peak_snr,
                    'INDEX_METHOD': self.index_method,
                    'INT_RADII': self.integration_radii,
                    'LOCAL_BG_RADIUS': self.local_bg_radius,
                    'MAX_RES': self.max_res,
                    'MIN_PEAKS': self.min_peaks,
                    'COPY_FIELDS': copy_fields,
                    'EXTRA_OPTIONS': self.indexamajig_extra_options
                })
        slurm_args = ['sbatch',
                      f'--partition={self.partition}',
                      f'--time={duration}',
                      f'--array=0-{n_nodes-1}',
                      f'./{prefix}_proc-{self.step}.sh']
        proc_out = subprocess.check_output(slurm_args, cwd=job_dir)
        return proc_out.decode('utf-8').split()[-1]    # job id

    def wrap_process(self, res_limit, cell_keyword, filtered=False):
        """ Perform the processing as distributed computation job;
            when finished combine the output and remove temporary files
        """
        self.step += 1

        # Prepare a directory to store indexamajig input and output
        job_dir = f"./indexamajig_{self.step}"
        utl.make_new_dir(job_dir)

        report_reconfig(self.list_prefix, self.overrides)
        n_frames = len(self.hit_list) if filtered else self.n_frames_total
        n_nodes = self.n_nodes_hits if filtered else self.n_nodes_all
        job_duration = self.duration_hits if filtered else self.duration_all
        if self.interactive:
            _duration = input(f'SLURM allocation time [{job_duration}] > ')
            if _duration != '':
                job_duration = _duration
        job_id = self.process_slurm_multi(job_dir, res_limit, cell_keyword,
                                          filtered=filtered)
        utl.wait_or_cancel(
            job_id,
            job_dir,
            n_frames,
            self._crystfel_version)
        self.concat(job_dir, filtered)
        stream_file_name = f'{self.list_prefix}_hits.stream' if filtered \
            else f'{self.list_prefix}.stream'
        report_step_rate(self.list_prefix, stream_file_name, self.step,
                         res_limit)
        # self.clean_up(job_id, filtered)
        if not self.diagnostic:
            utl.remove_path(job_dir)

    def check_cxi(self):
        """ Optional name-by-name confirmation or override of CXI file names;
            storage of experiment identifiers.
        """
        if self.interactive:
            for i, cxi_name in enumerate(self.cxi_names):
                _cxi_name = input(f'Cheetah-CXI file name [{cxi_name}] > ')
                if _cxi_name != '':
                    self.cxi_names[i] = _cxi_name

        for i, cxi_name in enumerate(self.cxi_names):
            if not os.path.exists(cxi_name):
                warnings.warn(f' File {cxi_name} not found!')
                exit(0)
            with h5py.File(cxi_name, 'r') as f:
                self.exp_ids.append(np.array(f['entry_1/experiment_identifier'][()]))
            print(f'Data set {i:02d}: {cxi_name} '
                  f'contains {self.exp_ids[i].shape[0]} frames in total.')

    def make_virtual(self):
        """ Make reference to original data in run folders, provide VDS for
            usage with indexamajig (CXI compliant format)
        """
        print('\n-----   TASK: check/create virtual data sets   -----')
        vds_mask_int = int(self.vds_mask, 16)
        print('Bad-pixel mask value for VDS, as from geom file: ' 
              f'{self.vds_mask} ({vds_mask_int})')

        if self.interactive:
            for i, vds_name in enumerate(self.vds_names):
                _vds_name = input(f'Virtual data set name [{vds_name}] > ')
                if _vds_name != '':
                    self.vds_names[i] = _vds_name

        for i, vds_name in enumerate(self.vds_names):
            if not (os.path.exists(f'{self.work_dir}/{vds_name}')
                    or os.path.exists(f'{vds_name}')):
                print('Creating a VDS file in CXI format ...')
                if self.interactive:
                    _data_path = input(f'Data path [{self.data_runs[i]}] > ')
                    if _data_path != '':
                        if os.path.exists(_data_path):
                            print(' [path check o.k.]')
                            self.data_runs[i] = _data_path
                        else:
                            print(' [path not found - config kept]')
                with open(f'_tmp_{self.list_prefix}_make_vds.sh', 'w') as f:
                    f.write(MAKE_VDS % {'DATA_PATH': self.data_runs[i],
                                        'VDS_NAME': vds_name,
                                        'MASK_BAD': vds_mask_int
                                        })
                subprocess.check_output(['sh', f'_tmp_{self.list_prefix}_make_vds.sh'])
            else:
                print(f'Requested VDS {vds_name} is present already.')

            with h5py.File(vds_name, 'r') as f:
                self.exp_ids.append(np.array(f['entry_1/experiment_identifier'][()]))
            print(f'Data set {i:02d}: {vds_name} '
                  f'contains {self.exp_ids[i].shape[0]} frames in total.')

    def transfer_geometry(self):
        """ Transfer corner x/y positions and fs/ss vectors onto a geometry
            file template in suited format (user ensures correct template)  
        """
        if self.interactive:
            _geom_template = \
                input(f'Path to geometry template [{self.geom_template}] > ')
            if _geom_template != '':
                if os.path.exists(_geom_template):
                    self.geom_template = _geom_template
                else:
                    warnings.warn(
                        'Cannot find file at designated path, default kept.')

        target_distance = geo.get_detector_distance(self.geometry)
        target_bad_pixel = geo.get_bad_pixel(self.geometry)
        target_photon_energy = geo.get_photon_energy(self.geometry)
        target_panel_corners = geo.get_panel_positions(self.geometry)
        target_panel_vectors = geo.get_panel_vectors(self.geometry)
        target_panel_offsets = geo.get_panel_offsets(self.geometry)
        out_fn = self.geometry + '_tf.geom'
        with open(out_fn, 'w') as of:
            of.write('; Geometry file written by EXtra-xwiz\n')
            of.write('; Geometry used: {}\n'.format(self.geometry))
            of.write('; Format template used: {}\n'.format(self.geom_template))
            with open(self.geom_template, 'r') as tf:
                for ln in tf:
                    if ln[:41] == '; Optimized panel offsets can be found at':
                        continue
                    if ln[:6] == 'clen =':
                        of.write('clen = {}\n'.format(target_distance))
                    elif ln[:15] == 'photon_energy =':
                        of.write('photon_energy = {}\n'.format(
                                                        target_photon_energy))
                    elif ln[:10] == 'mask_bad =':
                        of.write('mask_bad = {}\n'.format(target_bad_pixel))
                    elif ln[0] == 'p' and ('/corner_x' in ln or '/corner_y' in ln) and ' = ' in ln:
                        tile_id = ln.split()[0]
                        of.write(
                            '{} = {}\n'.format(tile_id,
                                               target_panel_corners[tile_id]))
                    elif ln[0] == 'p' and ('/fs =' in ln or '/ss =' in ln):
                        tile_id = ln.split()[0]
                        of.write(
                            '{} = {}\n'.format(tile_id,
                                               target_panel_vectors[tile_id]))
                    elif ln[0] == 'p' and '/coffset =' in ln:
                        tile_id = ln.split()[0]
                        of.write(
                            '{} = {}\n'.format(tile_id,
                                               target_panel_offsets[tile_id]))
                    else:
                       of.write(ln)
        self.geometry = out_fn

    def prep_distribute(self):
        """ Inquire enumerator and denominator of the frame distribution onto
            chunks: total number (in case truncated) and number of jobs/nodes
        """
        _nfr_offset = input(
            f'Frames offset in each datafile[{self.n_frames_offset}] > ')
        if _nfr_offset != '':
            try:
                self.n_frames_offset = int(_nfr_offset)
            except TypeError:
                warnings.warn(WARN_WRONG_TYPE)
        _nfr_percent = input(
            f'Percent of frames to process[{self.n_frames_percent}] > ')
        if _nfr_percent != '':
            try:
                self.n_frames_percent = int(_nfr_percent)
            except TypeError:
                warnings.warn(WARN_WRONG_TYPE)
        _nfr_max = input(
            f'Maximum frames per datafile[{self.n_frames_max}] > ')
        if _nfr_max != '':
            try:
                self.n_frames_max = int(_nfr_max)
            except TypeError:
                warnings.warn(WARN_WRONG_TYPE)
        _nfr_total = input(
            f'Number of frames to process [{self.n_frames_total}] > ')
        if _nfr_total != '':
            try:
                self.n_frames_total = int(_nfr_total)
            except TypeError:
                warnings.warn(WARN_WRONG_TYPE)

        _n_nodes = input(f'Number of nodes [{self.n_nodes_all}] > ')
        if _n_nodes != '':
            try:
                self.n_nodes_all = int(_n_nodes)
            except TypeError:
                warnings.warn(WARN_WRONG_TYPE)
        _list_prefix = input(f'List file-name prefix [{self.list_prefix}] > ')
        if _list_prefix != '':
            self.list_prefix = _list_prefix


    def distribute_data(self):
        """ Distribute the consecutive data frames as in the VDS or Cheetah-CXI
            accounting for the number to be processed, onto N chunks, and write
            into N temporary .lst files
        """
        print('\n-----   TASK: prepare distributed computing   -----')
        if self.interactive:
            self.prep_distribute()
        ds_names = self.cxi_names if self.use_peaks else self.vds_names
        n_data_files = len(ds_names)

        # Total number of frames in the datafiles
        nfr_raw = [self.exp_ids[i].shape[0] for i in range(n_data_files)]
        nfr_raw = np.array(nfr_raw)

        # Subtract offset
        nfr_offset = np.broadcast_to(self.n_frames_offset, nfr_raw.shape)
        nfr_cut_offset = np.maximum(nfr_raw - nfr_offset, 0)

        # Limit number of frames for each datafile
        nfr_max = np.broadcast_to(self.n_frames_max, nfr_raw.shape).copy()
        nfr_max[nfr_max < 0] = max(nfr_cut_offset)
        nfr_cut_max = np.minimum(nfr_cut_offset, nfr_max)

        # Take only specified percent of the frames
        nfr_perc = np.broadcast_to(self.n_frames_percent, nfr_raw.shape)
        nfr_cut_perc = (nfr_cut_max * nfr_perc/100).astype(int)

        # Select frames only up to n_frames_total
        nfr_cut_total = nfr_cut_perc.copy()
        sumfr_cut_total = sum(nfr_cut_total)
        if self.n_frames_total >= 0 and self.n_frames_total < sumfr_cut_total:
            nfr_left = self.n_frames_total
            for ids in range(n_data_files):
                if nfr_left > nfr_cut_total[ids]:
                    nfr_left -= nfr_cut_total[ids]
                else:
                    nfr_cut_total[ids] = nfr_left
                    nfr_cut_total[ids+1:] = 0
                    break
        else:
            self.n_frames_total = sumfr_cut_total
        print("Total number of frames to process:", sum(nfr_cut_total))

        # Make a list of datasets and frame indices
        frames_lst = list()
        for ids in range(n_data_files):
            for ifr in range(nfr_cut_total[ids]):
                frames_lst.append(f'{ds_names[ids]} //{ifr+nfr_offset[ids]}\n')

        # Split frames list per slurm node and write to files
        frames_lst_split = np.array_split(frames_lst, self.n_nodes_all)
        print("Split into:", end='')
        for ich, sub_frames_lst in enumerate(frames_lst_split):
            print(f" {len(sub_frames_lst)}", end='')
            with open(f'{self.list_prefix}_{ich}.lst', 'w') as flst:
                for line in sub_frames_lst:
                    flst.write(line)
        print()


    def distribute_cheetah(self):
        """ Distribute the number of Cheetah HDF5 files, accounting for the
            amount of frames to be processed, onto N chunks, and write the
            file paths into N temporary .lst files
        """
        print('\n-----   TASK: analyse and distribute Cheetah input   -----')
        n_files, average_n_frames = utl.scan_cheetah_proc_dir(self.data_path)
        print('total number of processed files:   {:5d}'.format(n_files))
        print('average number of frames per file: {:.1f}'.format(average_n_frames))
        print('estimated total number of frames:',
              int(average_n_frames * n_files))
        self.prep_distribute()
        n_used_files = int(round(self.n_frames_total / average_n_frames))
        if n_used_files > n_files:
            warnings.warn('Number of used files from requested number of'
                          f' frames exceeds total, reset to {n_files}.')
            n_used_files = n_files
        file_indices = np.array_split(np.arange(n_used_files), self.n_nodes_all)
        file_items = sorted([os.path.join(dp, f) for dp, dn, fn in os.walk(self.data_path) for f in fn])
        for chunk, indices in enumerate(file_indices):
            print(len(indices), end=' ')
            with open(f'{self.list_prefix}_{chunk}.lst', 'w') as f:
                for index in indices:
                    f.write(f'{file_items[index]}\n')
        print()

    def distribute_hits(self):
        """ Split up the list of indexed frames (also stored to one file) onto
            N chunks and write N temporary .lst files
        """
        if self.interactive:
            _n_nodes = input(f'Number of nodes [{self.n_nodes_hits}] > ')
            if _n_nodes != '':
                try:
                    self.n_nodes_hits = int(_n_nodes)
                except TypeError:
                    warnings.warn(WARN_WRONG_TYPE)
        n_filtered = len(self.hit_list)
        split_indices = np.array_split(np.arange(n_filtered), self.n_nodes_hits)
        for chunk, sub_indices in enumerate(split_indices):
            print(len(sub_indices), end=' ')
            with open(f'{self.list_prefix}_hits_{chunk}.lst', 'w') as f:
                for index in sub_indices:
                    f.write(f'{self.hit_list[index]}\n')
        print()

    def concat(self, job_dir, filtered=False):
        """ Concatenate CrystFEL stream files obtained from split-processing
        """
        # in case account for the fact the prefix_* covers prefix_hits_*
        prefix = f'{self.list_prefix}_hits' if filtered else self.list_prefix
        chunks = sorted(glob(f'{job_dir}/{prefix}_*.stream'))
        with open(f'{prefix}.stream', 'w') as f_out, fileinput.input(chunks) as f_in:
            for ln in f_in:
                f_out.write(ln)

    def clean_up(self, job_id, filtered=False):
        """ Remove files that are meant to be temporary as per splitting
        """
        prefix = f'{self.list_prefix}_hits' if filtered else self.list_prefix
        input_lists = glob(f'{prefix}_*.lst')
        stream_out = glob(f'{prefix}_*.stream')
        slurm_out = glob(f'slurm-{job_id}_*.out')
        file_items = input_lists + stream_out
        if not self.diagnostic:
            file_items += slurm_out
        for item in file_items:
            os.remove(item)

    def write_hit_list(self):
        """Write the total set of indexed frames into one 'hit list' file
        """
        list_file = self.list_prefix + '_hits.lst'
        with open(list_file, 'w') as f:
            for hit_event in self.hit_list:
                f.write(f'{hit_event}\n')

    def cell_explorer(self):
        """Identify initial unit cell from a relatively small number of frames
           indexed w/o prior cell
        """
        crystfel_import = cri.crystfel_info[self._crystfel_version]['import']

        with open('_cell_explorer.sh', 'w') as f:
            f.write(CELL_EXPLORER_WRAP % {
                'IMPORT_CRYSTFEL': crystfel_import,
                'PREFIX': self.list_prefix
            })
        subprocess.check_output(['sh', '_cell_explorer.sh'])
        _explorer_cell = ''
        while not os.path.exists(_explorer_cell):
            _explorer_cell = \
                input(' Name of the cell file created with cell explorer > ')
        self.cell_file = _explorer_cell
        """
        # the following is likely premature, respectively redundant if we have
          another SLURM-distributed run vs. all frames:
        self.hit_list, _ = \
            utl.get_crystal_frames(f'{self.list_prefix}.stream', self.cell_file)
        self.write_hit_list()
        """

    def fit_filtered_crystals(self):
        """Select diffraction frames from match vs. good cell
        """
        self.hit_list, self.cell_ensemble = \
            utl.get_crystal_frames(f'{self.list_prefix}.stream', self.cell_file,
                               self.cell_tolerance)
        print('Overall indexing rate is', len(self.hit_list) / self.n_frames_total)
        report_cell_check(self.list_prefix, len(self.hit_list), self.n_frames_total)
        self.write_hit_list()
        if self.cell_run_refine:
            print('\n-----   TASK: refine unit cell parameters   -----')
            refined_cell = utl.fit_unit_cell(self.cell_ensemble)
            utl.replace_cell(self.cell_file, refined_cell)
            self.cell_file = f'{self.cell_file}_refined'

    def merge_bragg_obs(self):
        """ Interface to the CrystFEL utilities for the 'merging' steps
        """

        # Prepare a directory to store partialator input and output
        part_dir = f"./partialator"
        utl.make_new_dir(part_dir)
        # Make links to the refined cell and output stream files
        utl.make_link(self.cell_file, part_dir)
        utl.make_link(f"{self.list_prefix}_hits.stream", part_dir)

        crystfel_import = cri.crystfel_info[self._crystfel_version]['import']

        # scale and average using partialator
        with open(f'{part_dir}/_tmp_partialator.sh', 'w') as f:
            f.write(PARTIALATOR_WRAP % {
                'IMPORT_CRYSTFEL': crystfel_import,
                'PREFIX': self.list_prefix,
                'POINT_GROUP': self.point_group,
                'N_ITER': self.scale_iter,
                'MODEL': self.scale_model,
                'MAX_ADU': self.max_adu
            })
        out = subprocess.check_output(['sh', '_tmp_partialator.sh'],
            cwd=part_dir, stderr=subprocess.STDOUT)

        log_items = []
        # create simple resolution-bin table
        with open(f'{part_dir}/_tmp_table_gen.sh', 'w') as f:
            f.write(CHECK_HKL_WRAP % {
                'IMPORT_CRYSTFEL': crystfel_import,
                'PREFIX': self.list_prefix,
                'POINT_GROUP': self.point_group,
                'UNIT_CELL': self.cell_file,
                'HIGH_RES': self.res_higher
            })
        out = subprocess.check_output(['sh', '_tmp_table_gen.sh', 'w'],
            cwd=part_dir, stderr=subprocess.STDOUT)
        log_items.extend(out.decode('utf-8').split())

        # create resolution-bin tables based on half-sets
        for i in range(3):
            with open(f'{part_dir}/_tmp_table_gen{i}.sh', 'w') as f:
                f.write(COMPARE_HKL_WRAP % {
                    'IMPORT_CRYSTFEL': crystfel_import,
                    'PREFIX': self.list_prefix,
                    'POINT_GROUP': self.point_group,
                    'UNIT_CELL': self.cell_file,
                    'HIGH_RES': self.res_higher,
                    'FOM': ['CC', 'CCstar', 'Rsplit'][i],
                    'FOM_TAG': ['cchalf', 'ccstar', 'rsplit'][i]
                })
            out = subprocess.check_output(['sh', f'_tmp_table_gen{i}.sh'],
                cwd=part_dir, stderr=subprocess.STDOUT)
            log_items.extend(out.decode('utf-8').split())

        for fn in glob(f'{part_dir}/_tmp*'):
            os.remove(fn)
        report_merging_metrics(part_dir, self.list_prefix, log_items)

    def process_late(self):
        """ Last pass of the workflow:
            re-indexing, integration and scaling/merging
        """
        print('\n-----   TASK: run CrystFEL with refined cell and filtered frames   ------')
        self.distribute_hits()
        res_limit, cell_keyword = \
            self.crystfel_from_config(high_res=self.res_higher)
        if self.interactive:
            _int_radii = input('Integration radii around predicted Bragg-peak'
                               f'positions [{self.integration_radii}] > ')
            if _int_radii != '':
                try:
                    _ = [int(x) for x in _int_radii.split(',')][:3]
                    self.integration_radii = _int_radii
                except ValueError:
                    warnings.warn('Wrong format or types for integration-radii parameter')
        self.wrap_process(res_limit, cell_keyword, filtered=True)
        report_total_rate(self.list_prefix, self.n_frames_total)
        report_cells(self.list_prefix, self.cell_info)

        print('\n-----   TASK: scale/merge data and create statistics -----')
        if self.interactive:
            _point_group = input(f'Point group symmetry [{self.point_group}] > ')
            if _point_group != '':
                if _point_group in POINT_GROUPS:
                    self.point_group = _point_group
                else:
                    warnings.warn('Point group not recognized')
                    print('[default kept]')
            _scale_model = input(f'Scaling model to use [{self.scale_model}] > ')
            if _scale_model != '':
                if _scale_model in ['unity', 'scsphere']:
                    self.scale_model = _scale_model
                else:
                    warnings.warn('Model type not recognized')
                    print('[default kept]')
            _scale_iter = input(f'Number of iterations [{self.scale_iter}] > ')
            if _scale_iter != '':
                try:
                    self.scale_iter = int(_scale_iter)
                except TypeError:
                    warnings.warn(WARN_WRONG_TYPE)

        self.merge_bragg_obs()

    def check_late_entrance(self):
        """ Verify the presence of mandatory files from a previous session
        """
        if self.interactive:
            _list_prefix = input(f'List file-name prefix [{self.list_prefix}] > ')
            if _list_prefix != '':
                self.list_prefix = _list_prefix
            _cell_file = input(f'Unit cell file [{self.cell_file}_refined] > ')
            if _cell_file == '':
                self.cell_file = f'{self.cell_file}_refined'
            else:
                self.cell_file = f'{_cell_file}_refined'
        n_issues = 0
        if not os.path.exists(f'{self.list_prefix}_hits.lst'):
            warnings.warn('Cannot find pre-selection of indexed detector frames')
            n_issues += 1
        if not os.path.exists(self.cell_file):
            warnings.warn('Cannot find cell file with refined unit cell')
            n_issues += 1
        if n_issues > 0:
            print(f'Found {n_issues} issues. Make sure you have run a workflow'
                  ' for the present configuration before.)')
            exit()
        self.hit_list = open(f'{self.list_prefix}_hits.lst').read().splitlines()

    def manage(self):
        """ Parent workflow structure implementation
        """
        create_new_summary(self.list_prefix, self.config, self.interactive,
                           self.use_cheetah)

        if self.reprocess:
            self.check_late_entrance()
            report_reprocess(self.list_prefix)
            self.process_late()
            return

        # principal modes of input and operation
        if self.use_cheetah:
            # Cheetah multi-folder HDF5 w/o peaks (rare)
            self.distribute_cheetah()
        else:
            # single CXI or VDS-CXI data set per run (common)
            if self.use_peaks:
                # real CXI data set from Cheetah with peaks
                self.check_cxi()
            else:
                # virtual CXI data set pointing to EuXFEL proc run
                self.make_virtual()
            self.distribute_data()

        print('\n-----   TASK: run CrystFEL (I)   -----')
        if self.interactive:
            _geometry = input(f'Path to geometry file [{self.geometry}] > ')
            if _geometry != '':
                if os.path.exists(_geometry):
                    self.geometry = _geometry
                    print(' [check o.k.]')
                else:
                    warnings.warn('Geometry file not found; default kept.')
        if geo.check_geom_format(self.geometry, self.use_peaks) == False:
            self.transfer_geometry()
            print(f' Geometry transferred to new file "{self.geometry}".')

        res_limit, cell_keyword = \
            self.crystfel_from_config(high_res=self.res_lower)
        self.wrap_process(res_limit, cell_keyword, filtered=False)

        if not os.path.exists(self.cell_file):
            print('\n-----   TASK: determine initial unit cell and re-run CrystFEL')
            # fit cell remotely, do not yet filter, but re-run with that
            self.cell_explorer()
            if self.use_peaks:
                self.distribute_cheetah()
            else:
                self.distribute_data()
            res_limit, cell_keyword = \
                self.crystfel_from_config(high_res=self.res_lower)
            self.wrap_process(res_limit, cell_keyword, filtered=False)

        print('\n-----   TASK: filter crystal frames according to the'
              ' unit cell parameters   -----')
        if self.interactive:
            _cell_tolerance = input(f'Match tolerance of frame-cells vs. expectation [{self.cell_tolerance}] > ')
            if _cell_tolerance != '':
                try:
                    self.cell_tolerance = float(_cell_tolerance)
                except TypeError:
                    warnings.warn('Wrong type; kept at default')
        # first filter indexed frames, then update cell based on crystals found
        self.fit_filtered_crystals()

        self.process_late()


def main(argv=None):
    ap = ArgumentParser(prog="xwiz-workflow")
    ap.add_argument(
        "-a", "--automatic",
        action='store_true',
        help="enable auto-pipeline workflow (skip configuration review)"
    )
    ap.add_argument(
        "-d", "--diagnostic",
        action='store_true',
        help="keep SLURM stdout captures for diagnoses in case of problems"
    )
    ap.add_argument(
        "-r", "--reprocess",
        action='store_true',
        help="enter workflow at the re-processing stage (refined unit "
             "cell and frame selection exist)"
    )
    ap.add_argument(
        "-p", "--peak-input",
        action='store_true',
        help="use a CXI data set file from Cheetah including pre-localized "
             "peaks"
    )
    ap.add_argument(
        "-c", "--cheetah-input",
        action='store_true',
        help="skip VDS generation and assemble input from Cheetah folder "
             "contents"
    )
    ap.add_argument(
        "-adv", "--advance-config",
        action='store_true',
        help="Generate an advanced config instead of the base one."
    )
    args = ap.parse_args(argv)
    home_dir = os.path.join('/home', os.getlogin())
    work_dir = os.getcwd()
    if not os.path.exists(f'{work_dir}/xwiz_conf.toml'):
        print('Configuration file is not present, will be created.')
        if args.advance_config:
            config.create_file(ADV_CONFIG)
        else:
            config.create_file(CONFIG)
        print('Please rerun now.')
        exit()
    elif args.advance_config:
        warnings.warn(
            "Ignore --advance-config option since config file already exists.")
    print(48 * '~')
    print(' xWiz - EXtra tool for pipelined SFX workflows')
    print(48 * '~')
    workflow = Workflow(home_dir, work_dir,
                        automatic=args.automatic,
                        diagnostic=args.diagnostic,
                        reprocess=args.reprocess,
                        use_peaks=args.peak_input,
                        use_cheetah=args.cheetah_input)
    workflow.manage()
    print(48 * '~')
    print(f' Workflow complete.\n See: {workflow.list_prefix}.summary')

