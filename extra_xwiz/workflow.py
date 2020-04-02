from argparse import ArgumentParser
import h5py
import numpy as np
import os
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
        self.n_nodes = conf['slurm']['n_nodes']

    def distribute(self):
        with h5py.File(self.vds_name, 'r') as f:
            self.exp_ids = np.array(f['entry_1/experiment_identifier'][()])
        print(self.exp_ids.shape)

    def manage(self):

        print(' xWiz - EXtra tool for pipelined SFX workflows')

        print('TASK: create virtual data set')
        if self.interactive:
            _data_path = input(f'data path [{self.data_path}] > ')
            if _data_path != '':
                if os.path.exists(_data_path):
                    print(' [check ok]')
                    self.data_path = _data_path
                else:
                    print(' [file not found - config kept]')
            _vds_name = input(f'virtual data set name [{self.vds_name}] > ')
            if _vds_name != '':
                self.vds_name = _vds_name
        os.system(f'extra-data-make-virtual-cxi {self.data_path} -o {self.vds_name}')

        print('TASK: prepare distributed computing')
        if self.interactive:
            _n_frames = input(f'number of frames [{self.n_frames}] > ')
            try:
                self.n_frames = int(_n_frames)
            except TypeError:
                pass
            _n_nodes = input(f'number of nodes [{self.n_nodes}] > ')
            try:
                self.n_nodes = int(_n_nodes)
            except TypeError:
                pass
        self.distribute()


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


