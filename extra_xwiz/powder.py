#!/gpfs/exfel/sw/software/xfel_anaconda3/1.1/bin/python
from argparse import ArgumentParser
import h5py as h5
import multiprocessing as mp
import numpy as np
import re
import sys
import time

'''
    idx = np.arange(numFrames, dtype=np.int32)
    k, m = divmod(numFrames, poolSize)
    chunks = [idx[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(poolSize)]


    args = []
    for n in range(poolSize):
        args.append([VDS_filename, chunks[n]])

'''

poolSize = mp.cpu_count() - 1
print('Number of available cores:', poolSize)

def read_size_from_file(fn):
    with h5.File(fn, 'r') as f:
        n_frames = len(f['/entry_1/data_1/data'])
    print(f'input data size: {n_frames} frames')
    return n_frames


def pix_max_over_frames(fn, n_frames):
    if (n_frames % 1000) == 0:
        n_chunks = n_frames / 1000
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
            data = _data[low:high]  # instantiation of array
            t2 = time.time()
            print(f'sub-max for range {low:5d} to {high:5d}') 
            _px_max.append(np.max(data, axis=0))
            t3 = time.time()
            print(f'reading: {(t2 - t1):.3f} s, maximizing: {(t3 - t2):.3f} s')
    px_max = np.max(np.stack(_px_max, axis=0), axis=0)
    print('pixel array:', px_max.shape)
    print('maxing finished.')
    return px_max

def write_vds(data, fn):
    data = np.expand_dims(data, axis=0)
    print('output data', data.shape)
    with h5.File(fn, 'w') as f:
        ds = f.create_dataset('entry_1/data_1/data', data=data)
    print('writing finished.')

def main(argv=None):
    ap = ArgumentParser(prog='make-virtual-cxi')
    ap.add_argument('vds_in', help='input VDS file name')
    ap.add_argument('vds_out', help='output VDS file name')
    args = ap.parse_args(argv)

    n_frames = read_size_from_file(args.vds_in)
    max_data = pix_max_over_frames(args.vds_in, n_frames)
    write_vds(max_data, args.vds_out)

