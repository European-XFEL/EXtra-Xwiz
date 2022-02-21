from argparse import ArgumentParser
import fileinput
from glob import glob
import h5py
import numpy as np
import os
import re
import shutil
import subprocess
import warnings

import findxfel as fdx

from . import config
from . import crystfel_info as cri
from . import geometry as geo
from . import utilities as utl
from . import templates as tmp
from . import summary as smr


class Workflow:

    def __init__(self, home_dir, work_dir, self_dir, automatic=False,
                 diagnostic=False, reprocess=False, use_peaks=False,
                 use_cheetah=False):
        """Construct a workflow instance from the pre-defined configuration.
           Initialize some class-global 'bookkeeping' variables
        """
        self.home_dir = home_dir
        self.work_dir = work_dir
        self.self_dir = self_dir
        self.interactive = not automatic
        self.diagnostic = diagnostic
        self.reprocess = reprocess
        self.use_peaks = use_peaks
        self.use_cheetah = use_cheetah
        self.cheetah_data_path = ''                        # for special cheetah tree
        self.exp_ids = []
        conf = config.load_from_file()

        if 'proposal' in conf['data']:
            self.data_proposal = conf['data']['proposal']
        elif 'path' in conf['data']:
            warnings.warn(
                "Configuration option 'data.path' is deprecated, please "
                "specify proposal number as 'data.proposal' instead."
            )
            mobj = re.search(r'/p(\d{6})', conf['data']['path'])
            if mobj is not None:
                self.data_proposal = int(mobj.group(1))
            else:
                raise ValueError(
                    "Could not retrieve proposal number from data path.")
        else:
            raise ValueError("Please provide proposal number in the config.")
        # 'runs' as a string with coma-separated values is deprecated
        if isinstance(conf['data']['runs'], str):
            warnings.warn(
                "'runs' as a comma-separated string is being deprecated, "
                "please use an integer or a list of integers instead."
            )
            self.data_runs = [
                int(val) for val in utl.string_to_list(conf['data']['runs'])
            ]
        else:
            self.data_runs = utl.into_list(conf['data']['runs'])
        self.set_data_runs_paths()

        # 'vds_names' as a string with coma-separated values is deprecated
        if (isinstance(conf['data']['vds_names'], str)
            and ',' in conf['data']['vds_names']):
            warnings.warn(
                "'vds_names' as a comma-separated string is being deprecated, "
                "please use a list of strings instead."
            )
            self.vds_names = utl.string_to_list(conf['data']['vds_names'])
        else:
            self.vds_names = utl.into_list(conf['data']['vds_names'])
        if not len(self.vds_names) == len(self.data_runs_paths):
            print('CONFIG ERROR: unequal numbers of VDS files and run-paths')
            exit(0)
        if 'cxi_names' in conf['data']:
            self.cxi_names = utl.into_list(conf['data']['cxi_names'])
        else:
            self.cxi_names = ['']

        if 'n_frames_offset' in conf['data']:
            self.n_frames_offset = utl.into_list(
                conf['data']['n_frames_offset'])
        # Check for deprecated parameter
        elif 'frame_offset' in conf['data']:
            warnings.warn(
                "'frame_offset' is being deprecated, please use "
                "'n_frames_offset' instead.")
            self.n_frames_offset = utl.into_list(conf['data']['frame_offset'])
        else:
            self.n_frames_offset = 0
        if 'n_frames_percent' in conf['data']:
            self.n_frames_percent = utl.into_list(
                conf['data']['n_frames_percent'])
        else:
            self.n_frames_percent = 100
        if 'n_frames_max' in conf['data']:
            self.n_frames_max = utl.into_list(
                conf['data']['n_frames_max'])
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
        self.indexamajig_n_cores = conf['proc_coarse']['n_cores']
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
        self.overrides = {}     # collect optional config overrides
        self.hit_list = []
        self.cell_ensemble = []
        self.cell_info = []
        self.step = 0
        # store total number of processed frames in the slurm jobs
        self.n_proc_frames_all = 0
        self.n_proc_frames_hits = 0

    def get_cell_keyword(self):
        """In case cell file exists - prepare a keyword for CrystFEL."""
        cell_keyword = ''
        # check cell file presence; expected 'true' for default or overwrite != 'none'
        if os.path.exists(self.cell_file):
            cell_keyword = f'-p {self.cell_file}'
            self.cell_info.append(utl.cell_as_string(self.cell_file))
            print(' [cell-file read - o.k.]')
        else:
            warnings.warn(
                'Unit cell file cannot be read - processing without '
                'prior crystal geometry.'
            )

        return cell_keyword

    def process_slurm_multi(self, job_dir, high_res, cell_keyword,
                            n_nodes, job_duration, filtered=False):
        """ Write a batch-script wrapper for indexamajig from the relevant
            configuration parameters and start a process by sbatch submission
        """
        crystfel_import = cri.crystfel_info[self._crystfel_version]['import']
        prefix = f'{self.list_prefix}_hits' if filtered else self.list_prefix

        # Move list files to the slurm directory
        for input_list in glob(f'{prefix}_*.lst'):
            shutil.move(input_list, job_dir)

        # Make links to the data, geometry and cell files
        if self.use_cheetah:
            # Not sure, needs to be tested
            utl.make_link(
                self.cheetah_data_path,
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
            if os.path.isabs(data_file_0):
                data_file_path = data_file_0
            else:
                data_file_path = f"{job_dir}/{data_file_0}"
            copy_fields = utl.get_copy_hdf5_fields(data_file_path)

        with open(f'{job_dir}/{prefix}_proc-{self.step}.sh', 'w') as f:
            if self.use_peaks:
                f.write(tmp.PROC_CXI_BASH_SLURM % {
                    'IMPORT_CRYSTFEL': crystfel_import,
                    'PREFIX': prefix,
                    'GEOM': geom_keyword,
                    'CRYSTAL': cell_keyword,
                    'CORES': self.indexamajig_n_cores,
                    'RESOLUTION': high_res,
                    'PEAKS_HDF5_PATH': self.peaks_path,
                    'INDEX_METHOD': self.index_method,
                    'INT_RADII': self.integration_radii,
                    'COPY_FIELDS': copy_fields,
                    'EXTRA_OPTIONS': self.indexamajig_extra_options
                })
            else:
                f.write(tmp.PROC_VDS_BASH_SLURM % {
                    'IMPORT_CRYSTFEL': crystfel_import,
                    'PREFIX': prefix,
                    'GEOM': geom_keyword,
                    'CRYSTAL': cell_keyword,
                    'CORES': self.indexamajig_n_cores,
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
                      f'--time={job_duration}',
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

        n_nodes = self.n_nodes_hits if filtered else self.n_nodes_all
        job_duration = self.duration_hits if filtered else self.duration_all

        n_frames = len(self.hit_list) if filtered else self.n_frames_total

        job_id = self.process_slurm_multi(
            job_dir, res_limit, cell_keyword, n_nodes, job_duration,
            filtered=filtered
        )
        n_proc_frames = utl.wait_or_cancel(
            job_id,
            job_dir,
            n_frames,
            self._crystfel_version)
        self.concat(job_dir, filtered)
        stream_file_name = f'{self.list_prefix}_hits.stream' if filtered \
            else f'{self.list_prefix}.stream'
        smr.report_step_rate(
            self.list_prefix, stream_file_name, self.step, res_limit,
            n_proc_frames
        )
        # self.clean_up(job_id, filtered)
        if not self.diagnostic:
            utl.remove_path(job_dir)
        return n_proc_frames

    def check_cxi(self):
        """ Optional name-by-name confirmation or override of CXI file names;
            storage of experiment identifiers.
        """
        if self.interactive:
            self.verify_data_config_cheetah()

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
        vds_mask_int = int(self.vds_mask, 16)
        print('Bad-pixel mask value for VDS, as from geom file: ' 
              f'{self.vds_mask} ({vds_mask_int})')

        if self.interactive:
            self.verify_data_config_vds()

        for i, vds_name in enumerate(self.vds_names):
            if not (os.path.exists(f'{self.work_dir}/{vds_name}')
                    or os.path.exists(f'{vds_name}')):
                print('Creating a VDS file in CXI format ...')
                with open(f'_tmp_{self.list_prefix}_make_vds.sh', 'w') as f:
                    f.write(tmp.MAKE_VDS % {'DATA_PATH': self.data_runs_paths[i],
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
        det_type = geo.get_detector_type(self.geometry)
        template_path = f'{self.self_dir}/resources'

        if self.use_peaks:
            if det_type == 'agipd':
                geom_template = f'{template_path}/agipd_cheetah.geom'
            elif det_type == 'jungfrau':
                geom_template = f'{template_path}/jf4m_cheetah.geom'
        else:
            if det_type == 'agipd':
                geom_template = f'{template_path}/agipd_vds.geom'
            elif det_type == 'jungfrau':
                geom_template = f'{template_path}/jf4m_vds.geom'
        print('! Using template file:', geom_template)

        target_distance = geo.get_detector_distance(self.geometry)
        target_bad_pixel = geo.get_bad_pixel(self.geometry)
        target_photon_energy = geo.get_photon_energy(self.geometry)
        target_panel_corners = geo.get_panel_positions(self.geometry)
        target_panel_vectors = geo.get_panel_vectors(self.geometry)
        target_panel_offsets = geo.get_panel_offsets(self.geometry)

        out_fn = os.path.split(self.geometry)[-1] + '_tf.geom'
        with open(out_fn, 'w') as of:
            of.write('; Geometry file written by EXtra-xwiz\n')
            of.write('; Geometry used: {}\n'.format(self.geometry))
            of.write('; Format template used: {}\n'.format(geom_template))
            with open(geom_template, 'r') as tf:
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

    def set_data_runs_paths(self):
        """Set values for a list of full paths to the data runs."""
        self.data_runs_paths = [
            fdx.find_run(self.data_proposal, run, True)
            for run in self.data_runs
        ]

    def verify_data_config_vds(self):
        """Verify data parameters for generating vds files in the
        interactive mode."""
        accepted, self.data_proposal = utl.user_input_type(
            "Proposal number", self.data_proposal, val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.proposal", self.data_proposal)

        accepted, self.data_runs = utl.user_input_list(
            "List of runs to process", self.data_runs,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.runs", self.data_runs)
        self.set_data_runs_paths()

        accepted, self.vds_names = utl.user_input_list(
            "Names of the VDS files", self.vds_names,
            val_type = str, n_elements = len(self.data_runs)
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.vds_names", self.vds_names)

    def verify_data_config_cheetah(self):
        """Verify cheetah files with the peaks data in the interactive
        mode."""
        accepted, self.cxi_names = utl.user_input_list(
            "Names of the Cheetah-CXI files", self.cxi_names,
            val_type = str
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.cxi_names", self.cxi_names)

    def verify_data_config_prefix(self):
        """Verify framework files prefix in the interactive mode."""
        accepted, self.list_prefix = utl.user_input_str(
            "Framework files prefix", self.list_prefix
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.list_prefix", self.list_prefix)

    def verify_data_config_n_frames(self):
        """Verify parameters related to the number of frames to be
        processed in the interactive mode."""
        n_data_files = len(self.exp_ids)

        accepted, self.n_frames_offset = utl.user_input_list(
            "Frames offset in each datafile", self.n_frames_offset,
            val_type = int, n_elements = n_data_files, broadcastable = True
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.n_frames_offset", self.n_frames_offset)

        accepted, self.n_frames_max = utl.user_input_list(
            "Maximum frames per datafile", self.n_frames_max,
            val_type = int, n_elements = n_data_files, broadcastable = True
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.n_frames_max", self.n_frames_max)

        accepted, self.n_frames_percent = utl.user_input_list(
            "Percent of frames to process", self.n_frames_percent,
            val_type = int, n_elements = n_data_files, broadcastable = True
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.n_frames_percent", self.n_frames_percent)

        accepted, self.n_frames_total = utl.user_input_type(
            "Total maximum number of frames to process", self.n_frames_total,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "data.n_frames_total", self.n_frames_total)

    def verify_geom_config(self):
        """Verify geometry file parameters in the interactive mode."""
        accepted, self.geometry = utl.user_input_path(
            "Path to the geometry file", self.geometry
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "geom.file_path", self.geometry)

    def verify_cell_config(self):
        """Verify cell file parameters in the interactive mode."""
        accepted, self.cell_file = utl.user_input_path(
            "Path to the cell parameters file", self.cell_file
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "unit_cell.file", self.cell_file)

        accepted, self.cell_run_refine = utl.user_input_type(
            "Refine cell parameters after the coarse CrystFEL run?",
            self.cell_run_refine, val_type = bool
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "unit_cell.run_refine", self.cell_run_refine)

    def verify_slurm_config_all(self):
        """Verify slurm parameters in the interactive mode for the
        coarse CrystFEL run."""
        accepted, self.partition = utl.user_input_str(
            "SLURM partition", self.partition
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "slurm.partition", self.partition)

        accepted, self.duration_all = utl.user_input_str(
            "SLURM jobs maximum duration", self.duration_all,
            re_format = r'\d{1,2}:\d{2}:\d{2}'
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "slurm.duration_all", self.duration_all)

        accepted, self.n_nodes_all = utl.user_input_type(
            "Number of nodes", self.n_nodes_all,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "slurm.n_nodes_all", self.n_nodes_all)

    def verify_slurm_config_hits(self):
        """Verify slurm parameters in the interactive mode for the
        CrystFEL refine run."""
        accepted, self.duration_hits = utl.user_input_str(
            "SLURM jobs maximum duration", self.duration_hits,
            re_format = r'\d{1,2}:\d{2}:\d{2}'
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "slurm.duration_hits", self.duration_hits)

        accepted, self.n_nodes_hits = utl.user_input_type(
            "Number of nodes", self.n_nodes_hits,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "slurm.n_nodes_hits", self.n_nodes_hits)

    def verify_indexamajig_config_all(self):
        """Verify CrystFEL parameters in the interactive mode for the
        coarse run."""
        cri_keys_str = " / ".join(cri.crystfel_info.keys())
        cri_keys_re = utl.list_to_re(cri.crystfel_info.keys())
        accepted, self._crystfel_version = utl.user_input_str(
            f"CrystFEL version ({cri_keys_str})", self._crystfel_version,
            cri_keys_re
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "crystfel.version", self._crystfel_version)

        accepted, self.res_lower = utl.user_input_type(
            "Processing resolution limit in Å for the coarse run",
            self.res_lower, val_type = float
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.resolution", self.res_lower)

        accepted, self.peak_method = utl.user_input_str(
            "Peak-finding method to use", self.peak_method
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.peak_method", self.peak_method)

        accepted, self.peak_threshold = utl.user_input_type(
            "Peak threshold", self.peak_threshold,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.peak_threshold",
                self.peak_threshold
            )

        accepted, self.peak_snr = utl.user_input_type(
            "Peak minimum signal-to-noise", self.peak_snr,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.peak_snr", self.peak_snr)

        accepted, self.peak_min_px = utl.user_input_type(
            "Peak minimum size in pixels", self.peak_min_px,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.peak_min_px", self.peak_min_px)

        accepted, self.peak_max_px = utl.user_input_type(
            "Peak maximum size in pixels", self.peak_max_px,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.peak_max_px", self.peak_max_px)

        accepted, self.peaks_path = utl.user_input_str(
            "Path to the peaks data in case of Cheetah CXI with peaks",
            self.peaks_path
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.peaks_hdf5_path", self.peaks_path)

        accepted, self.index_method = utl.user_input_str(
            "Indexing method", self.index_method
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.index_method", self.index_method)

        accepted, self.local_bg_radius = utl.user_input_type(
            "Radius in pixels for local background estimation",
            self.local_bg_radius, val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.local_bg_radius",
                self.local_bg_radius
            )

        accepted, self.max_res = utl.user_input_type(
            "Maximum radius from the detector center to accepted peaks",
            self.max_res, val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.max_res", self.max_res)

        accepted, self.min_peaks = utl.user_input_type(
            "Minimum number of peaks to try indexing", self.min_peaks,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.min_peaks", self.min_peaks)

        accepted, self.indexamajig_n_cores = utl.user_input_type(
            "Number of cores to be used by each CrystFEL job",
            self.indexamajig_n_cores, val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.n_cores",
                self.indexamajig_n_cores
            )

        accepted, self.indexamajig_extra_options = utl.user_input_str(
            "Any extra CrystFEL options", self.indexamajig_extra_options
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_coarse.extra_options",
                self.indexamajig_extra_options
            )

    def verify_indexamajig_config_hits(self):
        """Verify CrystFEL parameters in the interactive mode for the
        refine run."""
        accepted, self.res_higher = utl.user_input_type(
            "Processing resolution limit in Å for the refine run",
            self.res_higher, val_type = float
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_fine.resolution", self.res_higher)

        accepted, self.integration_radii = utl.user_input_str(
            "Integration radii around predicted Bragg-peak positions",
            self.integration_radii, re_format = r'\d,\d,\d'
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "proc_fine.integration_radii",
                self.integration_radii
            )

    def verify_frame_filter_config(self):
        """Verify frame filter parameters in the interactive mode."""
        accepted, self.cell_tolerance = utl.user_input_type(
            "Match tolerance of frame-cells vs. expectation",
            self.cell_tolerance, val_type = float
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "frame_filter.match_tolerance",
                self.cell_tolerance
            )

    def verify_merging_config(self):
        """Verify reflections merging parameters in the interactive
        mode."""
        point_groups_re = utl.list_to_re(tmp.POINT_GROUPS)
        accepted, self.point_group = utl.user_input_str(
            "Reflections merging symmetry point group", self.point_group,
            re_format = point_groups_re
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "merging.point_group", self.point_group)

        accepted, self.scale_model = utl.user_input_str(
            "Partiality model", self.scale_model
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "merging.scaling_model", self.scale_model)

        accepted, self.scale_iter = utl.user_input_type(
            "Number of scaling and post refinement cycles", self.scale_iter,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "merging.scaling_iterations", self.scale_iter)

        accepted, self.max_adu = utl.user_input_type(
            "Maximum peak value to be merged", self.max_adu,
            val_type = int
        )
        if accepted:
            utl.set_dotdict_val(
                self.overrides, "merging.max_adu", self.max_adu)


    def distribute_data(self):
        """ Distribute the consecutive data frames as in the VDS or Cheetah-CXI
            accounting for the number to be processed, onto N chunks, and write
            into N temporary .lst files
        """
        print('\n-----   TASK: prepare distributed computing   -----\n')
        ds_names = self.cxi_names if self.use_peaks else self.vds_names
        n_data_files = len(self.exp_ids)

        # Total number of frames in the datafiles
        nfr_raw = [self.exp_ids[i].shape[0] for i in range(n_data_files)]
        nfr_raw = np.array(nfr_raw)

        # Subtract offset
        nfr_offset = np.broadcast_to(self.n_frames_offset, nfr_raw.shape).copy()
        if any(nfr_offset < 0):
            warnings.warn("n_frames_offset is forced to be >= 0.")
            nfr_offset[nfr_offset < 0] = 0
        nfr_cut_offset = np.maximum(nfr_raw - nfr_offset, 0)

        # Limit number of frames for each datafile
        nfr_max = np.broadcast_to(self.n_frames_max, nfr_raw.shape).copy()
        nfr_max[nfr_max < 0] = max(nfr_cut_offset)
        nfr_cut_max = np.minimum(nfr_cut_offset, nfr_max)

        # Take only specified percent of the frames
        nfr_perc = np.broadcast_to(self.n_frames_percent, nfr_raw.shape).copy()
        if any(nfr_perc < 0) or any(nfr_perc > 100):
            warnings.warn("n_frames_percent is forced to be within [0, 100].")
            nfr_perc[nfr_perc < 0] = 0
            nfr_perc[nfr_perc > 100] = 100
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
        print('\n-----   TASK: analyse and distribute Cheetah input   -----\n')
        n_files, average_n_frames = utl.scan_cheetah_proc_dir(self.cheetah_data_path)
        print('total number of processed files:   {:5d}'.format(n_files))
        print('average number of frames per file: {:.1f}'.format(average_n_frames))
        print('estimated total number of frames:',
              int(average_n_frames * n_files))
        n_used_files = int(round(self.n_frames_total / average_n_frames))
        if n_used_files > n_files:
            warnings.warn('Number of used files from requested number of'
                          f' frames exceeds total, reset to {n_files}.')
            n_used_files = n_files
        file_indices = np.array_split(np.arange(n_used_files), self.n_nodes_all)
        file_items = sorted([os.path.join(dp, f) for dp, dn, fn in os.walk(self.cheetah_data_path) for f in fn])
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
            f.write(tmp.CELL_EXPLORER_WRAP % {
                'IMPORT_CRYSTFEL': crystfel_import,
                'PREFIX': self.list_prefix
            })
        subprocess.check_output(['sh', '_cell_explorer.sh'])
        _, self.cell_file = utl.user_input_path(
            "Path to the cell parameters file created with the cell explorer")


    def fit_filtered_crystals(self):
        """Select diffraction frames from match vs. good cell
        """
        self.hit_list, self.cell_ensemble = \
            utl.get_crystal_frames(
                f'{self.list_prefix}.stream', self.cell_file,
                self.cell_tolerance
            )
        n_cryst = len(self.hit_list)
        index_rate = 100.0 * n_cryst / self.n_proc_frames_all
        print(f"Overall indexing rate is {index_rate:5.2f} %")
        smr.report_cell_check(
            self.list_prefix, n_cryst, self.n_proc_frames_all
        )
        self.write_hit_list()
        if self.cell_run_refine:
            print('\n-----   TASK: refine unit cell parameters   -----\n')
            refined_cell = utl.fit_unit_cell(self.cell_ensemble)
            utl.replace_cell(self.cell_file, refined_cell)
            self.cell_file = utl.get_refined_cell_name(self.cell_file)

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
            f.write(tmp.PARTIALATOR_WRAP % {
                'IMPORT_CRYSTFEL': crystfel_import,
                'PREFIX': self.list_prefix,
                'POINT_GROUP': self.point_group,
                'N_ITER': self.scale_iter,
                'MODEL': self.scale_model,
                'MAX_ADU': self.max_adu
            })
        subprocess.check_output(['sh', '_tmp_partialator.sh'],
            cwd=part_dir, stderr=subprocess.STDOUT)

        log_items = []
        # create simple resolution-bin table
        with open(f'{part_dir}/_tmp_table_gen.sh', 'w') as f:
            f.write(tmp.CHECK_HKL_WRAP % {
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
                f.write(tmp.COMPARE_HKL_WRAP % {
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
        smr.report_merging_metrics(part_dir, self.list_prefix, log_items)

    def process_late(self):
        """ Last pass of the workflow:
            re-indexing, integration and scaling/merging
        """
        print('\n-----   TASK: run CrystFEL with refined cell and filtered frames   ------\n')

        # Verify SLURM nodes config for the second CrystFEL run:
        if self.interactive:
            self.verify_slurm_config_hits()
            self.verify_indexamajig_config_hits()

        self.distribute_hits()
        cell_keyword = self.get_cell_keyword()

        self.n_proc_frames_hits = self.wrap_process(
            self.res_higher, cell_keyword, filtered=True)
        smr.report_total_rate(self.list_prefix, self.n_proc_frames_all)
        smr.report_cells(self.list_prefix, self.cell_info)

        print('\n-----   TASK: scale/merge data and create statistics -----\n')
        if self.interactive:
            self.verify_merging_config()

        self.merge_bragg_obs()

        # report all config parameters modified in the interactive mode
        smr.report_reconfig(self.list_prefix, self.overrides)


    def check_late_entrance(self):
        """ Verify the presence of mandatory files from a previous session
        """
        if self.interactive:
            self.verify_data_config_prefix()
            self.verify_cell_config()
            if self.cell_run_refine:
                self.cell_file = utl.get_refined_cell_name(self.cell_file)
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
        # verify framework files prefix
        if self.interactive:
            self.verify_data_config_prefix()

        smr.create_new_summary(
            self.list_prefix, self.config, self.interactive, self.use_cheetah)

        if self.reprocess:
            self.check_late_entrance()
            smr.report_reprocess(self.list_prefix)
            self.process_late()
            return

        print('\n-----   TASK: check / prepare data   -----\n')

        if not self.use_cheetah:
            if self.use_peaks:
                # real CXI data set from Cheetah with peaks
                self.check_cxi()
            else:
                # virtual CXI data set pointing to EuXFEL proc run
                self.make_virtual()

        print('\n-----   TASK: distribute data over SLURM nodes   -----\n')

        if self.interactive:
            self.verify_data_config_n_frames()
            self.verify_slurm_config_all()

        # principal modes of input and operation
        if self.use_cheetah:
            # Cheetah multi-folder HDF5 w/o peaks (rare)
            self.distribute_cheetah()
        else:
            # single CXI or VDS-CXI data set per run (common)
            self.distribute_data()

        print('\n-----   TASK: run CrystFEL (I)   -----\n')

        if self.interactive:
            self.verify_geom_config()
        if geo.check_geom_format(self.geometry, self.use_peaks) == False:
            self.transfer_geometry()
            print(f'! Geometry transferred to new file "{self.geometry}".')

        if self.interactive:
            self.verify_cell_config()
        cell_keyword = self.get_cell_keyword()

        if self.interactive:
            self.verify_indexamajig_config_all()

        self.n_proc_frames_all = self.wrap_process(
            self.res_lower, cell_keyword, filtered=False)

        if not os.path.exists(self.cell_file):
            print('\n-----   TASK: determine initial unit cell and re-run '
                  'CrystFEL   -----\n')
            # fit cell remotely, do not yet filter, but re-run with that
            self.cell_explorer()
            cell_keyword = self.get_cell_keyword()
            self.n_proc_frames_all = self.wrap_process(
                self.res_lower, cell_keyword, filtered=False)

        print('\n-----   TASK: filter crystal frames according to the'
              ' unit cell parameters   -----\n')
        if self.interactive:
            self.verify_frame_filter_config()
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
    self_dir = os.path.split(os.path.realpath(__file__))[0]
    if not os.path.exists(f'{work_dir}/xwiz_conf.toml'):
        print('Configuration file is not present, will be created.')
        if args.advance_config:
            config.create_file(tmp.ADV_CONFIG)
        else:
            config.create_file(tmp.CONFIG)
        print('Please rerun now.')
        exit()
    elif args.advance_config:
        warnings.warn(
            "Ignore --advance-config option since config file already exists.")
    print(48 * '~')
    print(' xWiz - EXtra tool for pipelined SFX workflows')
    print(48 * '~')
    workflow = Workflow(home_dir, work_dir, self_dir,
                        automatic=args.automatic,
                        diagnostic=args.diagnostic,
                        reprocess=args.reprocess,
                        use_peaks=args.peak_input,
                        use_cheetah=args.cheetah_input)
    workflow.manage()
    print(48 * '~')
    print(f' Workflow complete.\n See: {workflow.list_prefix}.summary')

