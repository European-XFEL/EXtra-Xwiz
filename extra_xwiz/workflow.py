from argparse import ArgumentParser
import h5py
import numpy as np
import os
import warnings

from . import config


class Workflow:

    def __init__(self, home_dir, work_dir, interactive=False):

        self.home_dir = home_dir
        self.work_dir = work_dir
        self.interactive = interactive
        self.exp_ids = np.array([])
        conf = config.load_from_file()
        self.data_path = conf['data']['path']
        self.vds_name = conf['data']['vds_name']
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
        self.unit_cell = conf['proc_coarse']['unit_cell']

    def crystfel_from_config(self):

        _peak_method = input(f'Peak-finding method to use [{self.peak_method}] > ')
        if _peak_method != '':
            if _peak_method in ['peakfinder8', 'zaef']:
                self.peak_method = _peak_method
            else:
                warnings.warn('Peak-finding method not known; default kept.')

        _index_method = input (f'indexing method to use [{self.index_method}] > ')
        if _index_method != '':
            if _index_method in ['mosflm', 'xds', 'xgandalf']:
                self.index_method = _index_method
            else:
                warnings.warn('Indexing method not known; default kept.')

        _cell = input(f'unit cell file to use as estimation [{self.unit_cell}] OR [none] > ')
        if _cell != '':
            if os.path.exists(_cell):
                self.unit_cell = _cell
                print(' [check o.k.]')
            else:
                # this will include the deliberate 'none'
                if _cell != 'none':
                    warnings.warn('Cell file not found. Set to none.')
                else:
                    warnings.warn('Processing without cell requested.')
                self.unit_cell = None

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

    def manage(self):

        print(' xWiz - EXtra tool for pipelined SFX workflows')

        print('TASK: create virtual data set')
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
        os.system(f'extra-data-make-virtual-cxi {self.data_path} -o {self.vds_name}')

        print('TASK: prepare distributed computing')
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

        print('TASK: run CrystFEL - lower resolution limit')
        if self.interactive:
            _partition = input(f'SLURM partition [{self.partition}] > ')
            if _partition != '':
                if _partition in ['exfel', 'upex']:
                    self.partition = _partition
                else:
                    warnings.warn('Partition not known; kept at default.')

            _duration = input(f'SLURM allocation time [{self.duration}] > ')
            if _duration != '':
                self.duration = _duration
            _resolution = input(f'Processing resolution limit [{self.res_lower}] > ')
            if _resolution != '':
                try:
                    self.res_lower = float(_resolution)
                except TypeError:
                    warnings.warn('Wrong type; kept at default')
            self.crystfel_from_config()


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
    if not os.path.exists(f'{home_dir}/.xwiz_conf.toml'):
        print('configuration file is not present, will be created.')
        config.create_file()
    workflow = Workflow(home_dir, work_dir, interactive=args.interactive)
    workflow.manage()


