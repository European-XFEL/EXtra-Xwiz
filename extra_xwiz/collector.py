#!/gpfs/exfel/sw/software/xfel_anaconda3/1.1/bin/python

from argparse import ArgumentParser
import numpy as np
import re
from subprocess import check_output
import sys

from extra_xwiz.templates import (PROC_VDS_BASH_SLURM, PARTIALATOR_WRAP,
                                  CHECK_HKL_WRAP, COMPARE_HKL_WRAP,
                                  CELL_EXPLORER_WRAP, POINT_GROUPS)

from extra_xwiz.utilities import wait_or_cancel

from extra_xwiz import config


def sort_by_event(framelist):
    raw_list = [(e, int(e.split('//')[-1])) for e in framelist]
    sorted_list = [item[0] for item in sorted(raw_list, key=lambda x: x[1])]
    return sorted_list

def add_constants(constants, lines):
    labels = ['a', 'b', 'c', 'al', 'be', 'ga']
    for i, tag in enumerate(labels):
        for ln in lines:
            if ' = ' in ln and ln.split(' = ')[0] == tag:
                constants[i].append(float(ln.split()[2]))
                break

def write_cell(constants, fn):
    labels = ['a', 'b', 'c', 'al', 'be', 'ga']
    with open(fn, 'r') as f_in:
        template_lines = f_in.readlines()
    with open(f'{fn}_refined', 'w') as f_out:
        for ln in template_lines:
            if ' = ' in ln:
                tag = ln.split(' = ')[0]
                if tag in labels:
                    ix = labels.index(tag)
                    unit = ['A', 'deg'][ix >= 3]
                    f_out.write(f'{tag} = {constants[ix]:.2f} {unit}\n')
                else:
                    f_out.write(ln)
            else:
                f_out.write(ln)


def make_master(run_nums):
    entries = []
    for r in run_nums:
        try:
            with open(f'r{r:03d}/p2697_r{r:03d}_hits.lst', 'r') as f_in:
                entries.extend(sort_by_event(f_in.readlines()))
            print(f' pool has {len(entries):5d} frames after run {r}')
        except FileNotFoundError:
            print(' Could not open file.')

    with open('master.lst', 'w') as f_out:
        for e in entries:
            r = e.split('_')[1]
            f_out.write(f'r{r}/{e}')
 
    return entries


def make_chunks(entries, n_chunks=10):
    sub_entries = np.array_split(entries, n_chunks)
    for i, chunk in enumerate(sub_entries):
        print(len(chunk), end=' ')
        with open(f'frames_{i}.lst', 'w') as f:
            for e in chunk:
                r = e.split('_')[1]
                f.write(f'r{r}/{e}')


def average_cell(run_nums, cell_file):
    cell_constants = [[] for i in range(6)]
    for r in run_nums:
        try:
            with open(f'r{r:03d}/{cell_file}_refined', 'r') as f_in:
                add_constants(cell_constants, f_in.readlines())
        except FileNotFoundError:
            print(' Could not open file.')
            exit(0)
    ac = [np.mean(cell_constants[i]) for i in range(6)]
    write_cell(ac, cell_file)


def process_frames(conf, n_frames, n_chunks=10):
    cell_file = conf['proc_coarse']['unit_cell']
    partition = conf['slurm']['partition']
    n_nodes = conf['slurm']['n_nodes_all']
    duration = conf['slurm']['duration_all']
    with open(f'process.sh', 'w') as f:
        f.write(PROC_VDS_BASH_SLURM % {
                'PREFIX': 'frames',
                'GEOM': conf['geom']['file_path'],
                'CRYSTAL': f'-p {cell_file}',
                'CORES': 40,
                'RESOLUTION': conf['proc_fine']['resolution'],
                'PEAK_METHOD': conf['proc_coarse']['peak_method'],
                'PEAK_THRESHOLD': conf['proc_coarse']['peak_threshold'],
                'PEAK_MIN_PX': conf['proc_coarse']['peak_min_px'],
                'PEAK_SNR': conf['proc_coarse']['peak_snr'],
                'INDEX_METHOD': conf['proc_coarse']['index_method'],
                'INT_RADII': conf['proc_fine']['integration_radii']
        })
    slurm_args = ['sbatch',
                  f'--partition={partition}',
                  f'--time={duration}',
                  f'--array=0-{n_nodes-1}',
                  f'./process.sh']
    proc_out = check_output(slurm_args)
    job_id = proc_out.decode('utf-8').split()[-1]    # job id
    wait_or_cancel(job_id, n_chunks, n_frames, duration)


def main(argv=None):
    ap = ArgumentParser(prog='make-virtual-cxi')
    ap.add_argument('runs', help='comma-separated list of run numbers')
    ap.add_argument('-n', '--n-chunks', default=10,
        help='number of chunks to distribute runs onto')
    args = ap.parse_args(argv)

    try:
        run_nums = [int(r) for r in args.runs.split(',')]
    except ValueError:
        print(' Run list not understood')
        exit(0)

    conf = config.load_from_file()
    entries = make_master(run_nums)
    cell_file = conf['proc_coarse']['unit_cell']
    if cell_file[-5:] == '.cell':
        average_cell(run_nums, cell_file)
    elif cell_file[-8:] == '_refined':
        print(' taking pre-refined cell.')

    make_chunks(entries, n_chunks = args.n_chunks)
    process_frames(conf, len(entries), n_chunks = args.n_chunks)

