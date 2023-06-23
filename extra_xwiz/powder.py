#!/gpfs/exfel/sw/software/xfel_anaconda3/1.1/bin/python
from argparse import ArgumentParser
import h5py as h5
import multiprocessing as mp
import numpy as np
import re
import subprocess
import sys
import time

from . import config
from . import crystfel_info as cri
from .templates import HDFSEE_WRAP

'''
    idx = np.arange(numFrames, dtype=np.int32)
    k, m = divmod(numFrames, poolSize)
    chunks = [idx[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(poolSize)]


    args = []
    for n in range(poolSize):
        args.append([VDS_filename, chunks[n]])

poolSize = mp.cpu_count() - 1
print('Number of available cores:', poolSize)
'''

def read_size_from_file(fn):
    with h5.File(fn, 'r') as f:
        n_frames = len(f['/entry_1/data_1/data'])
    print(f'input data size: {n_frames} frames')
    return n_frames


def pix_max_over_frames(fn, n_frames):
    if (n_frames % 1000) == 0:
        n_chunks = int(n_frames / 1000)
    else: 
        n_chunks = n_frames // 1000 + 1
    print(f'will find max in {n_chunks} chunks.')
    _px_max = []

    with h5.File(fn, 'r') as f:
        _data = f['/entry_1/data_1/data'] # reference only
        for i in range(n_chunks):
            low = 1000 * i
            high = min(1000 * (i+1), n_frames)
            t1 = time.time()
            # data = _data[low:high]  # instantiation of array
            data = np.zeros((high-low,) + _data.shape[1:], dtype=_data.dtype)
            k = 0
            for j in range(low, high):
                data[k] = _data[j]
                k += 1
            t2 = time.time()
            print(f'sub-max for range {low:5d} to {high:5d}')
            data[np.isnan(data)] = 0.
            _px_max.append(np.max(data, axis=0))
            t3 = time.time()
            print(f'reading: {(t2 - t1):.3f} s, maximizing: {(t3 - t2):.3f} s')
    px_max = np.max(np.stack(_px_max, axis=0), axis=0)
    print('pixel array:', px_max.shape)
    print('maxing finished.')
    return px_max


def write_hdf5(data, fn):
    data = np.expand_dims(data, axis=0)
    print('output data', data.shape)
    with h5.File(fn, 'w') as f:
        ds = f.create_dataset('entry_1/data_1/data', data=data)
    print('writing finished.')


def display_hdf5(fn, geom, crystfel_version):
    crystfel_import = cri.crystfel_info[crystfel_version]['import']

    with open('_hdfsee.sh', 'w') as f:
        f.write(HDFSEE_WRAP % {
            'IMPORT_CRYSTFEL': crystfel_import,
            'DATA_FILE': fn,
            'GEOM': geom
        })
    subprocess.check_output(['sh', '_hdfsee.sh'])


def main(argv=None):
    ap = ArgumentParser(prog='powder.py')
    ap.add_argument('vds_in', help='input VDS file name (multi-frame data)')
    ap.add_argument('h5_out', help='output HDF5 file name (virtual powder image)')
    ap.add_argument('--display', help='optional display')
    args = ap.parse_args(argv)

    conf = config.load_from_file()
    n_frames = read_size_from_file(args.vds_in)
    crystfel_version = conf['crystfel']['version']
    max_frames = conf['data']['n_frames_total']
    geom = conf['geom']['file_path']
    if max_frames < n_frames:
        print(f' truncation to {max_frames} frames.')
    n_frames = int(min(n_frames, max_frames))
    max_data = pix_max_over_frames(args.vds_in, n_frames)
    write_hdf5(max_data, args.h5_out)
    if args.display is None:
    	display_hdf5(args.h5_out, geom, crystfel_version)

