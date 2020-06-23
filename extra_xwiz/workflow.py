from argparse import ArgumentParser
import fileinput
from glob import glob
import h5py
import numpy as np
import os
import subprocess
import warnings

from . import config
from .templates import (PROC_BASH_SLURM, PROC_BASH_DIRECT, PARTIALATOR_WRAP,
                        CHECK_HKL_WRAP, COMPARE_HKL_WRAP, CELL_EXPLORER_WRAP,
                        POINT_GROUPS, MAKE_VDS)
from .utilities import (wait_or_cancel, wait_single, get_crystal_frames,
                        fit_unit_cell, replace_cell, cell_as_string,
                        scan_cheetah_proc_dir)
from .summary import (create_new_summary, report_cell_check, report_step_rate,
                      report_total_rate, report_cells, report_merging_metrics,
                      report_reprocess)


class Workflow:

    def __init__(self, home_dir, work_dir, automatic=False, reprocess=False,
                 use_cheetah=False):

        self.home_dir = home_dir
        self.work_dir = work_dir
        self.interactive = not automatic
        self.reprocess = reprocess
        self.use_cheetah = use_cheetah
        self.exp_ids = np.array([])
        conf = config.load_from_file()
        self.data_path = conf['data']['path']
        self.vds_name = conf['data']['vds_name']
        self.geometry = conf['data']['geometry']
        self.n_frames = conf['data']['n_frames']
        self.list_prefix = conf['data']['list_prefix']
        self.n_nodes = conf['slurm']['n_nodes']
        self.partition = conf['slurm']['partition']
        self.duration = conf['slurm']['duration']
        self.res_lower = conf['proc_coarse']['resolution']
        self.res_higher = conf['proc_fine']['resolution']
        self.peak_method = conf['proc_coarse']['peak_method']
        self.peak_threshold = conf['proc_coarse']['peak_threshold']
        self.peak_snr = conf['proc_coarse']['peak_snr']
        self.peak_min_px = conf['proc_coarse']['peak_min_px']
        self.index_method = conf['proc_coarse']['index_method']
        self.cell_file = conf['proc_coarse']['unit_cell']
        self.cell_tolerance = conf['frame_filter']['match_tolerance']
        self.integration_radii = conf['proc_fine']['integration_radii']
        self.point_group = conf['merging']['point_group']
        self.scale_model = conf['merging']['scaling_model']
        self.scale_iter = conf['merging']['scaling_iterations']
        self.max_adu = conf['merging']['max_adu']
        self.hit_list = []
        self.cell_ensemble = []
        self.cell_info = []
        self.step = 0

    def crystfel_from_config(self, high_res=2.0):

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
                else:
                    warnings.warn('Peak-finding method not known; default kept.')

            _peak_threshold = input(f'Peak threshold [{self.peak_threshold}] > ')
            if _peak_threshold != '':
                try:
                    self.peak_threshold = int(_peak_threshold)
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _peak_snr = input(f'Peak min. signal-to-noise [{self.peak_snr}] > ')
            if _peak_snr != '':
                try:
                    self.peak_snr = int(_peak_snr)
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _peak_min_px = input(f'Peak min. pixel count [{self.peak_min_px}] > ')
            if _peak_min_px != '':
                try:
                    self.peak_min_px = int(_peak_min_px)
                except TypeError:
                    warnings.warn('Wrong type; kept at default')

            _index_method = input(f'indexing method to use [{self.index_method}] > ')
            if _index_method != '':
                if _index_method in ['mosflm', 'xds', 'xgandalf']:
                    self.index_method = _index_method
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
            self.cell_info.append(cell_as_string(self.cell_file))
            print(' [cell-file check o.k.]')
        elif self.cell_file != 'none':
            warnings.warn('Processing without unit cell due to invalid cell file.')

        return high_res, cell_keyword

    def process_slurm_multi(self, high_res, cell_keyword):

        with open(f'{self.list_prefix}_proc-0.sh', 'w') as f:
            f.write(PROC_BASH_SLURM % {'PREFIX': self.list_prefix,
                                       'GEOM': self.geometry,
                                       'CRYSTAL': cell_keyword,
                                       'CORES': 40,
                                       'RESOLUTION': high_res,
                                       'PEAK_METHOD': self.peak_method,
                                       'PEAK_THRESHOLD': self.peak_threshold,
                                       'PEAK_MIN_PX': self.peak_min_px,
                                       'PEAK_SNR': self.peak_snr,
                                       'INDEX_METHOD': self.index_method
                                       })
        slurm_args = ['sbatch',
                      f'--partition={self.partition}',
                      f'--time={self.duration}',
                      f'--array=0-{self.n_nodes-1}',
                      f'./{self.list_prefix}_proc-0.sh']
        proc_out = subprocess.check_output(slurm_args)
        return proc_out.decode('utf-8').split()[-1]    # job id

    def process_slurm_single(self, high_res, cell_keyword):

        if self.interactive:
            _int_radii = input('Integration radii around predicted Bragg-peak'
                               f'positions [{self.integration_radii}] > ')
            if _int_radii != '':
                try:
                    _ = [int(x) for x in _int_radii.split(',')]
                    self.integration_radii = _int_radii
                except ValueError:
                    warnings.warn('Wrong format or types for integration-radii parameter')

        with open(f'{self.list_prefix}_proc-1.sh', 'w') as f:
            f.write(PROC_BASH_DIRECT % {'PREFIX': self.list_prefix,
                                        'GEOM': self.geometry,
                                        'CRYSTAL': cell_keyword,
                                        'CORES': 40,
                                        'RESOLUTION': high_res,
                                        'PEAK_METHOD': self.peak_method,
                                        'PEAK_THRESHOLD': self.peak_threshold,
                                        'PEAK_MIN_PX': self.peak_min_px,
                                        'PEAK_SNR': self.peak_snr,
                                        'INDEX_METHOD': self.index_method,
                                        'INT_RADII': self.integration_radii
                                        })
        slurm_args = ['sbatch',
                      f'--partition={self.partition}',
                      f'--time={self.duration}',
                      f'./{self.list_prefix}_proc-1.sh']
        proc_out = subprocess.check_output(slurm_args)
        return proc_out.decode('utf-8').split()[-1]  # job id

    def wrap_process(self):
        self.step += 1
        res_limit, cell_keyword = \
            self.crystfel_from_config(high_res=self.res_lower)
        job_id = self.process_slurm_multi(res_limit, cell_keyword)
        wait_or_cancel(job_id, self.n_nodes, self.n_frames, self.duration)
        self.concat()
        report_step_rate(self.list_prefix, f'{self.list_prefix}.stream',
                         self.step, res_limit)
        self.clean_up(job_id)

    def make_virtual(self):
        print('\n-----   TASK: create virtual data set   -----')
        if self.interactive:
            _vds_name = input(f'Virtual data set name [{self.vds_name}] > ')
            if _vds_name != '':
                self.vds_name = _vds_name
        if not ( os.path.exists(f'{self.work_dir}/{self.vds_name}') or os.path.exists(f'{self.vds_name}') ):
            with open(f'_tmp_{self.list_prefix}_make_vds.sh', 'w') as f:
                f.write(MAKE_VDS % {'DATA_PATH': self.data_path,
                                    'VDS_NAME': self.vds_name
                                    })
            subprocess.check_output(['sh', f'_tmp_{self.list_prefix}_make_vds.sh'])
            #os.system(f'/gpfs/exfel/sw/software/xfel_anaconda3/1.1/bin/extra-data-make-virtual-cxi {self.data_path} -o {self.vds_name}')
        else:
            print('Requested VDS is present already.')
        with h5py.File(self.vds_name, 'r') as f:
            self.exp_ids = np.array(f['entry_1/experiment_identifier'][()])
        print(f'Data set contains {self.exp_ids.shape[0]} frames in total.')

    def prep_distribute(self):

        print('\n-----   TASK: prepare distributed computing   -----')
        if self.interactive:
            _n_frames = input(f'Number of frames to process [{self.n_frames}] > ')
            if _n_frames != '':
                try:
                    self.n_frames = int(_n_frames)
                except TypeError:
                    warnings.warn('Wrong type; kept at default.')
            _n_nodes = input(f'Number of nodes [{self.n_nodes}] > ')
            if _n_nodes != '':
                try:
                    self.n_nodes = int(_n_nodes)
                except TypeError:
                    warnings.warn('Wrong type; kept at default.')
            _list_prefix = input(f'List file-name prefix [{self.list_prefix}] > ')
            if _list_prefix != '':
                self.list_prefix = _list_prefix

    def distribute_vds(self):

        self.prep_distribute()
        if self.n_frames > self.exp_ids.shape[0]:
            warnings.warn('Requested number of frames too large, reset to'
                          f' total frame number of {self.exp_ids.shape[0]}.')
            self.n_frames = self.exp_ids.shape[0]
        sub_indices = np.array_split(np.arange(self.n_frames), self.n_nodes)
        for chunk, indices in enumerate(sub_indices):
            print(len(indices), end=' ')
            with open(f'{self.list_prefix}_{chunk}.lst', 'w') as f:
                for index in indices:
                    f.write(f'{self.vds_name} //{index}\n')
        print()

    def distribute_cheetah(self):
        print('\n-----   TASK: analyse and distribute Cheetah input   -----')
        n_files, average_n_frames = scan_cheetah_proc_dir(self.data_path)
        print('total number of processed files:   {:5d}'.format(n_files))
        print('average number of frames per file: {:.1f}'.format(average_n_frames))
        print('estimated total number of frames:',
              int(average_n_frames * n_files))
        self.prep_distribute()
        n_used_files = int(round(self.n_frames / average_n_frames))
        if n_used_files > n_files:
            warnings.warn('Number of used files from requested number of'
                          f' frames exceeds total, reset to {n_files}.')
            n_used_files = n_files
        file_indices = np.array_split(np.arange(n_used_files), self.n_nodes)
        file_items = sorted([os.path.join(dp, f) for dp, dn, fn in os.walk(self.data_path) for f in fn])
        for chunk, indices in enumerate(file_indices):
            print(len(indices), end=' ')
            with open(f'{self.list_prefix}_{chunk}.lst', 'w') as f:
                for index in indices:
                    f.write(f'{file_items[index]}\n')
        print()

    def concat(self):

        chunks = sorted(glob(f'{self.list_prefix}_*.stream'))
        with open(f'{self.list_prefix}.stream', 'w') as f_out, fileinput.input(chunks) as f_in:
            for ln in f_in:
                f_out.write(ln)

    def clean_up(self, job_id):

        input_lists = glob(f'{self.list_prefix}_*.lst')
        stream_out = glob(f'{self.list_prefix}_*.stream')
        slurm_out = glob(f'slurm-{job_id}_*.out')
        file_items = input_lists + stream_out + slurm_out
        for item in file_items:
            os.remove(item)

    def write_hit_list(self):

        list_file = self.list_prefix + '_hits.lst'
        with open(list_file, 'w') as f:
            for hit_event in self.hit_list:
                f.write(f'{hit_event}\n')

    def cell_explorer(self):
        """Identify initial unit cell from a relatively small number of frames
           indexed w/o prior cell
        """
        with open('_cell_explorer.sh', 'w') as f:
            f.write(CELL_EXPLORER_WRAP % {'PREFIX': self.list_prefix})
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
            get_crystal_frames(f'{self.list_prefix}.stream', self.cell_file)
        self.write_hit_list()
        """

    def fit_filtered_crystals(self):
        """Select diffraction frames from match vs. good cell
        """
        self.hit_list, self.cell_ensemble = \
            get_crystal_frames(f'{self.list_prefix}.stream', self.cell_file,
                               self.cell_tolerance)
        print('Overall indexing rate is', len(self.hit_list) / self.n_frames)
        report_cell_check(self.list_prefix, len(self.hit_list), self.n_frames)
        self.write_hit_list()
        refined_cell = fit_unit_cell(self.cell_ensemble)
        replace_cell(self.cell_file, refined_cell)
        self.cell_file = f'{self.cell_file}_refined'

    def merge_bragg_obs(self):

        # scale and average using partialator
        with open('_tmp_partialator.sh', 'w') as f:
            f.write(PARTIALATOR_WRAP % {
                'PREFIX': self.list_prefix,
                'POINT_GROUP': self.point_group,
                'N_ITER': self.scale_iter,
                'MODEL': self.scale_model,
                'MAX_ADU': self.max_adu
            })
        subprocess.check_output(['sh', '_tmp_partialator.sh'])

        # create simple resolution-bin table
        with open('_tmp_table_gen.sh', 'w') as f:
            f.write(CHECK_HKL_WRAP % {
                'PREFIX': self.list_prefix,
                'POINT_GROUP': self.point_group,
                'UNIT_CELL': self.cell_file,
                'HIGH_RES': self.res_higher
            })
        subprocess.check_output(['sh', '_tmp_table_gen.sh', 'w'])

        # create resolution-bin tables based on half-sets
        for i in range(3):
            with open(f'_tmp_table_gen{i}.sh', 'w') as f:
                f.write(COMPARE_HKL_WRAP % {
                    'PREFIX': self.list_prefix,
                    'POINT_GROUP': self.point_group,
                    'UNIT_CELL': self.cell_file,
                    'HIGH_RES': self.res_higher,
                    'FOM': ['CC', 'CCstar', 'Rsplit'][i],
                    'FOM_TAG': ['cchalf', 'ccstar', 'rsplit'][i]
                })
            subprocess.check_output(['sh', f'_tmp_table_gen{i}.sh'])

        for fn in glob('_tmp*'):
            os.remove(fn)
        report_merging_metrics(self.list_prefix)

    def process_late(self):

        print('\n-----   TASK: run final CrystFEL with refined cell ------')
        self.step += 1
        res_limit, cell_keyword = self.crystfel_from_config(high_res=self.res_higher)
        job_id = self.process_slurm_single(res_limit, cell_keyword)
        wait_single(job_id, len(self.hit_list))
        report_step_rate(self.list_prefix, f'{self.list_prefix}_hits.stream',
                         self.step, res_limit)
        report_total_rate(self.list_prefix, self.n_frames)
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
                    warnings.warn('Wrong type; kept at default.')

        self.merge_bragg_obs()

    def check_late_entrance(self):

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

        if self.reprocess:
            self.check_late_entrance()
            report_reprocess(self.list_prefix)
            self.process_late()
            return

        if self.interactive:
            _data_path = input(f'Data path [{self.data_path}] > ')
            if _data_path != '':
                if os.path.exists(_data_path):
                    print(' [check o.k.]')
                    self.data_path = _data_path
                else:
                    print(' [file not found - config kept]')

        if self.use_cheetah:
            self.distribute_cheetah()
        else:
            self.make_virtual()
            self.distribute_vds()

        print('\n-----   TASK: run CrystFEL (I)   -----')
        if self.interactive:
            _geometry = input(f'VDS-compatible geometry file [{self.geometry}] > ')
            if _geometry != '':
                if os.path.exists(_geometry):
                    self.geometry = _geometry
                    print(' [check o.k.]')
                else:
                    warnings.warn('Geometry file not found; default kept.')

            _partition = input(f'SLURM partition [{self.partition}] > ')
            if _partition != '':
                if _partition in ['exfel', 'upex']:
                    self.partition = _partition
                else:
                    warnings.warn('Partition not known; kept at default.')

            _duration = input(f'SLURM allocation time [{self.duration}] > ')
            if _duration != '':
                self.duration = _duration

        create_new_summary(self.list_prefix, self.geometry)
        self.wrap_process()

        if self.cell_file == 'none':
            print('\n-----   TASK: determine initial unit cell and re-run CrystFEL')
            # fit cell remotely, do not yet filter, but re-run with that
            self.cell_explorer()
            self.distribute()
            self.wrap_process()

        print('\n-----   TASK: check crystal frames and refine unit cell -----')
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
        "-a", "--automatic", help="enable auto-pipeline workflow"
        " (skip configuration review)",
        action='store_true'
    )
    ap.add_argument(
        "-r", "--reprocess", help="enter workflow at the re-processing stage"
        " (refined unit cell and frame selection exist)",
        action='store_true'
    )
    ap.add_argument(
        "-c", "--cheetah-input", help="skip VDS generation and assemble input"
        " from Cheetah folder contents",
        action='store_true'
    )
    args = ap.parse_args(argv)
    home_dir = os.path.join('/home', os.getlogin())
    work_dir = os.getcwd()
    if not os.path.exists(f'{work_dir}/.xwiz_conf.toml'):
        print('Configuration file is not present, will be created.')
        config.create_file()
        print('Please rerun now.')
        exit()
    print(48 * '~')
    print(' xWiz - EXtra tool for pipelined SFX workflows')
    print(48 * '~')
    workflow = Workflow(home_dir, work_dir,
                        automatic=args.automatic,
                        reprocess=args.reprocess,
                        use_cheetah=args.cheetah_input)
    workflow.manage()
    print(48 * '~')
    print(f' Workflow complete.\n See: {workflow.list_prefix}.summary')
