from argparse import ArgumentParser
import h5py
import numpy as np
import os
import subprocess
import warnings

from . import config
from .templates import PROC_BASH
from .utilities import wait_or_cancel


class Workflow:

    def __init__(self, home_dir, work_dir, interactive=False):

        self.home_dir = home_dir
        self.work_dir = work_dir
        self.interactive = interactive
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
        self.index_method = conf['proc_coarse']['index_method']
        self.cell_file = conf['proc_coarse']['unit_cell']

    def crystfel_from_config(self, high_res=2.0):

        cell_keyword = ''

        if self.interactive:
            _resolution = input(f'Processing resolution limit [{high_res}] > ')
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

            _index_method = input(f'indexing method to use [{self.index_method}] > ')
            if _index_method != '':
                if _index_method in ['mosflm', 'xds', 'xgandalf']:
                    self.index_method = _index_method
                else:
                    warnings.warn('Indexing method not known; default kept.')

            _cell_file = input(f'unit cell file to use as estimate [{self.cell_file}] OR ["none"] > ')
            if _cell_file != '':
                if _cell_file == 'none':
                    print('Processing without prior unit cell (unknown crystal geometry).')
                self.cell_file = _cell_file

        # check cell file presence; expected 'true' for default or overwrite != 'none'
        if os.path.exists(self.cell_file):
            cell_keyword = f'-p {self.cell_file}'
            print(' [check o.k.]')
        elif _cell_file != 'none':
            warnings.warn('Processing without prior unit cell (invalid cell file).')

        with open(f'{self.list_prefix}_proc-0.sh', 'w') as f:
            f.write(PROC_BASH % {'PREFIX': self.list_prefix,
                                 'GEOM': self.geometry,
                                 'CRYSTAL': cell_keyword,
                                 'CORES': 40,
                                 'RESOLUTION': high_res,
                                 'PEAK_METHOD': self.peak_method,
                                 'PEAK_THRESHOLD': self.peak_threshold,
                                 'PEAK_SNR': self.peak_snr,
                                 'INDEX_METHOD': self.index_method
                                 })
        slurm_args = ['sbatch',
                      f'--partition={self.partition}',
                      f'--time={self.duration}',
                      f'--array=0-{self.n_nodes}',
                      f'./{self.list_prefix}_proc-0.sh']

        # print(' '.join(slurm_args))
        proc_out = subprocess.check_output(slurm_args)
        return proc_out.decode('utf-8').split()[-1]    # job id

    def distribute(self):

        with h5py.File(self.vds_name, 'r') as f:
            self.exp_ids = np.array(f['entry_1/experiment_identifier'][()])
        n_total = self.exp_ids.shape[0]
        if self.n_frames > n_total:
            warnings.warn('Requested number of frames too large, reset to'
                          'total frame number.')
            self.n_frames = n_total
        sub_indices = np.array_split(np.arange(self.n_frames), self.n_nodes)
        for chunk, indices in enumerate(sub_indices):
            print(len(indices), end=' ')
            with open(f'{self.list_prefix}_{chunk}.lst', 'w') as f:
                for index in indices:
                    f.write(f'{self.vds_name} //{index}\n')
        print()

    def manage(self):

        print('\n-----   TASK: create virtual data set   -----')
        if self.interactive:
            _data_path = input(f'Data path [{self.data_path}] > ')
            if _data_path != '':
                if os.path.exists(_data_path):
                    print(' [check o.k.]')
                    self.data_path = _data_path
                else:
                    print(' [file not found - config kept]')
            _vds_name = input(f'Virtual data set name [{self.vds_name}] > ')
            if _vds_name != '':
                self.vds_name = _vds_name
        if not os.path.exists(f'{self.work_dir}/{self.vds_name}'):
            os.system(f'extra-data-make-virtual-cxi {self.data_path} -o {self.vds_name}')
        else:
            print('Requested VDS is present already.')

        print('\n-----   TASK: prepare distributed computing   -----')
        if self.interactive:
            _n_frames = input(f'Number of frames [{self.n_frames}] > ')
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
        self.distribute()

        print('\n-----   TASK: run CrystFEL (I) - moderate resolution   -----')
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

        jobid = self.crystfel_from_config(high_res=self.res_lower)
        wait_or_cancel(jobid, self.n_nodes, self.n_frames, self.duration)
        print('\n-----   TASK: check unit cells -----')


def main(argv=None):
    ap = ArgumentParser(prog="extra-xwiz")
    ap.add_argument(
        "-i", "--interactive", help="screen through configuration"
        " interactively",
        action='store_true'
    )
    args = ap.parse_args(argv)
    home_dir = os.path.join('/home', os.getlogin())
    work_dir = os.getcwd()
    if not os.path.exists(f'{work_dir}/.xwiz_conf.toml'):
        print('configuration file is not present, will be created.')
        config.create_file()
    print(' xWiz - EXtra tool for pipelined SFX workflows')
    workflow = Workflow(home_dir, work_dir, interactive=args.interactive)
    workflow.manage()


