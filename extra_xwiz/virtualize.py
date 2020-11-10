from glob import glob
import h5py as h5
import numpy as np
from  os.path import split as pathsplit
import re
import sys

from .utilities import print_simple_bar

H5_ROOT = 'INSTRUMENT/SPB_IRDA_JF4M/DET/JNGFR'
DTYPES = {'adc': np.float32, 'gain': np.uint8, 'mask': np.uint32,
          'memoryCell': np.uint8, 'frameNumber': np.uint64 }
VDS_SPEC = {'adc': 'data', 'gain': 'gain', 'mask': 'mask',
            'memoryCell': 'cellId', 'frameNumber': 'frameNumber' }

def check_run_length(run_path):

    print(f'pre-scanning run length at path: {run_path}')
    jf_seqfs = sorted(glob(f'{run_path}/*JNGFR01-S000??.h5'))
    nmcells = [[] for i in range(3)]
    ntrains = [[] for i in range(3)]
    nframes = [0, 0, 0]
    for i, seq_fn in enumerate(jf_seqfs):
        with h5.File(seq_fn, 'r') as f:
            for j, item in enumerate(['adc', 'gain', 'mask']):
                ds = f[f'{H5_ROOT}01:daqOutput']['data'][item]
                dim_sz = ds.shape
                print(f'{seq_fn} {item:4s} {dim_sz}')
                nframes[j] += dim_sz[0] * dim_sz[1]
                ntrains[j].append(dim_sz[0])
                nmcells[j].append(dim_sz[1])
    print(f'Run contains {nframes[0]} frames, as per module #1')
    print(f'  arranged in {sum(ntrains[0])} trains X {nmcells[0][0]} memory cells.')
    return nframes[0], ntrains[0], nmcells[0][0], jf_seqfs


def write_jf_vds(run_path, out_fn, nframes, ntrains, nmcells, seqfs):

    print(f'mapping data from path: {run_path}')
    tail_fn = pathsplit(seqfs[0])[-1]
    stem_fn = tail_fn[:tail_fn.find('-JNGFR')]
    print(f'stem file name:', stem_fn)

    with h5.File(out_fn, 'w') as wf:

        # pixel-image data sets
        for item in ['adc', 'gain', 'mask']:
            print(f'\n - Mapping data set: {item}')
            sys.stdout.flush()
            layout = h5.VirtualLayout((nframes, 8, 512, 1024), dtype=DTYPES[item]) 

            u = 0  # unit step
            for mod_num in range(1, 9):
                k = 0  # frame number
                for seq_num in range(len(seqfs)):
                    if k == nframes:
                        print('WARNING: frame limit reached ... ending here.')
                        break
                    fn = f'{run_path}/{stem_fn}-JNGFR{mod_num:02d}-S{seq_num:05d}.h5'
                    with h5.File(fn, 'r') as rf:
                        ds = rf[f'{H5_ROOT}{mod_num:02d}:daqOutput']['data'][item]
    
                        for i in range(ntrains[seq_num]):
                            for j in range(nmcells):
                                layout[k, mod_num-1, :, :] = h5.VirtualSource(ds)[i, j]
                                k += 1
                                u += 1
                    print_simple_bar(u, 8 * nframes, length=50)

            wf.create_virtual_dataset(f'entry_1/instrument_1/detector_1/{VDS_SPEC[item]}', layout)

        # cellId and frameNum: REAL ntrains x ncells per module/file 
        #  --> VIRTUAL: nframes x module
        for item in ['memoryCell', 'frameNumber']:
            print(f'\n - Mapping data set: {item}')
            sys.stdout.flush()
            layout = h5.VirtualLayout((nframes, 8), dtype=DTYPES[item])

            u = 0  # unit step
            for mod_num in range(1, 9):
                k = 0  # frame number
                for seq_num in range(len(seqfs)):
                    if k == nframes:
                        print('WARNING: frame limit reached ... ending here.')
                        break
                    fn = f'{run_path}/{stem_fn}-JNGFR{mod_num:02d}-S{seq_num:05d}.h5'
                    with h5.File(fn, 'r') as rf:
                        ds = rf[f'{H5_ROOT}{mod_num:02d}:daqOutput']['data'][item]

                        for i in range(ntrains[seq_num]):
                            for j in range(nmcells):
                                layout[k, mod_num-1] = h5.VirtualSource(ds)[i, j]
                                k += 1
                                u += 1
                    print_simple_bar(u, 8 * nframes, length=50)

            wf.create_virtual_dataset(f'entry_1/{VDS_SPEC[item]}', layout)

        # trainId / pulseId: REAL ntrains -> VIRTUAL nframes (expand by factor
        #    cells-per-train)   ! CAVEAT: pulseId not available from original,
        #    will fill in memory cell index instead !
        for item in ['trainId', 'pulseId']:
            print(f'\n - Mapping data set: {item}')
            sys.stdout.flush()
            layout = h5.VirtualLayout((nframes,), dtype=np.uint64)

            k = 0
            for seq_num in range(len(seqfs)):
                if k == nframes:
                    print('WARNING: frame limit reached ... ending here.')
                    break
                fn = f'{run_path}/{stem_fn}-JNGFR01-S{seq_num:05d}.h5'
                with h5.File(fn, 'r') as rf:
                    source = [item, 'memoryCell'][item == 'pulseId']
                    ds = rf[f'{H5_ROOT}01:daqOutput']['data'][source]
                    for i in range(ntrains[seq_num]):
                        for j in range(nmcells):
                            q = [i, j][item == 'pulseId']
                            layout[k] = h5.VirtualSource(ds)[q]
                            k += 1
           
            wf.create_virtual_dataset(f'entry_1/{item}', layout)

        # reference to a real data set with frame-wise strings (1d-array),
        #     of 'experiment IDs': trainId:cellId
        id_ds = wf.create_dataset('entry_1/experiment_identifier',
                                 shape=(nframes,),
                                 dtype=h5.special_dtype(vlen=str))
        exp_ids = []
        for seq_num in range(len(seqfs)):
            fn = f'{run_path}/{stem_fn}-JNGFR01-S{seq_num:05d}.h5'
            with h5.File(fn, 'r') as rf:
                ds = rf[f'{H5_ROOT}01:daqOutput']['data']['trainId']
                cell_id = rf[f'{H5_ROOT}01:daqOutput']['data']['memoryCell']
                for i in range(ntrains[seq_num]):
                    for j in range(nmcells):
                        exp_ids.append(f'{ds[i]}:{cell_id[i, j]}')
           
        id_ds[:] = np.array(exp_ids)

        # soft-links creating alternatively used (shortcut) HDF5 paths
        wf['entry_1/data_1'] = h5.SoftLink('/entry_1/instrument_1/detector_1')
        wf['entry_1/instrument_1/detector_1/experiment_identifier'] = \
            h5.SoftLink('/entry_1/experiment_identifier')

