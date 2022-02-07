"""
Functions to parse the relevant detector geometry from a file and write
additional information to the geometry file.
"""

import os
import warnings

from . import utilities as utl

def check_geom_format(geometry, use_peaks):
    """ Verify that the provided geometry file is compatible to respective
        data file: VDS-CXI or Cheetah-CXI.
    """
    with open(geometry, 'r') as f:
        # XFEL-VDS case with dim 1 = mod-ix, dim 2 = ss, ss resets
        if not use_peaks:
            for ln in f:
                if 'max_ss' in ln and not 'bad' in ln and int(ln.split()[-1]) > 511:
                    warnings.warn(f'Geometry file {geometry} is not compatible'
                                  ' to EuXFEL-VDS')
                    return False
        # Cheetah-CXI case with continuous slow-scan (dim 1 = ss)
        else:
            panels_max_ss = []
            for ln in f:
                if 'max_ss' in ln and not 'bad' in ln:
                    panels_max_ss.append(int(ln.split()[-1]))
                if '/dim1 = 0' in ln:
                    warnings.warn(f'Geometry file {geometry} is not compatible'
                                  ' to Cheetah-CXI')
                    return False
            if max(panels_max_ss) <= 511:
                warnings.warn(f'Geometry file {geometry} is not compatible to'
                              ' Cheetah-CXI')
                return False
    print('Geometry file is format-compatible to corresponding data')
    return True


def get_detector_type(fn):
    """ Read the pixel size to tell AGIPD-1M from JUNGFRAU-4M.
        Send a critical error if the found value does not comply to either
    """
    pixel_res = ''
    with open(fn) as f:
        for ln in f:
            if ln[:5] == 'res =':
                pixel_res = ln.split()[2]
                break
        if pixel_res == '5000' or pixel_res == '5000.0':
            return 'agipd'
        elif pixel_res == '13333.3':
            return 'jungfrau'
        else:
            print('Fatal error: could not verify detector type'
                  'Termination due to unresolved geometry format')
            exit(0)

def get_detector_distance(fn):
    """ Read the sample-to-detector distance (aka "camera length")
    """
    with open(fn) as f:
        for ln in f:
            if ln[:6] == 'clen =':
                return ln.split()[2]  # mustn't use [-1], beware of comments!
        print(' Warning: "clen" keyword not found')
        return '0.9999'

def get_photon_energy(fn):
    """ Read the photon energy (equivalent to wavelength)
    """
    with open(fn) as f:
        for ln in f:
            if ln[:15] == 'photon_energy =':
                return ln.split()[2]  # must't use [-1], beware of comments!
        print(' Warning: "photon_energy" keyword not found')
        return '9999'


def get_bad_pixel(fn):
    """ Read the integer bit-value for bad pixels (mask)
    """
    default_val = '0xffff'
    with open(fn) as f:
        for ln in f:
            # Get rid of comments
            ln = ln.partition(';')[0]
            if 'mask_bad' in ln:
                mask_bad_val = ln.partition('=')[2].strip()
                # Check if the value can be converted from hex to int
                try:
                    _ = int(mask_bad_val, 16)
                except ValueError:
                    warnings.warn(
                        f'\n Illegal "mask_bad" in the geometry: {mask_bad_val}.'
                        f'\n Using the default of {default_val}.'
                    )
                    mask_bad_val = default_val
                return mask_bad_val
        warnings.warn(
            f'\n No "mask_bad" keyword in the geometry file.'
            f'\n Using the default of {default_val}.'
        )
        return default_val


def get_panel_positions(fn):
    """ Read all positional origins ("corners") of tiles
    """
    pos_dict = {}
    with open(fn) as f:
        for ln in f:
            if ln[0] == 'p' and ('/corner_x =' in ln or '/corner_y =' in ln):
                tile_id = ln.split()[0]
                pos_dict[tile_id] = ln.split()[-1]
    return pos_dict


def get_panel_vectors(fn):
    """ Read all fs/ss vectors ("tilts") of tiles
    """
    vec_dict = {}
    with open(fn) as f:
        for ln in f:
            if ln[0] == 'p' and ('/fs =' in ln or '/ss =' in ln):
                tile_id = ln.split()[0]
                vec_dict[tile_id] = ' '.join(ln.split()[-2:])
    return vec_dict


def get_panel_offsets(fn):
    """ Read all center offsets of tiles
    """
    off_dict = {}
    with open(fn) as f:
        for ln in f:
            if ln[0] == 'p' and '/coffset =' in ln:
                tile_id = ln.split()[0]
                off_dict[tile_id] = ln.split()[-1]
    return off_dict


def geom_add_hd5mask(geometry, mask_dict):
    """
    Copy geometry file to mask_dict['output'] and replace all geometry
    'mask*' parameters with HD5 mask parameters from mask_dict.

    Args:
        geometry (string): path to the existing geometry file.
        mask_dict (dict): dictionary with the HD5 mask parameters:
            {
            'mask_file' (string): path to the HD5 file with mask.
            'mask' (string): path to the mask inside HD5 file.
            'mask_good' (int): value for not masked detector pixels.
            'mask_bad' (int): value for masked detector pixels.
            'output' (string): folder or file to which the existing
                geometry file should be copied.
            }

    Returns:
        string: path to the new geometry file.
    """
    mask_file = mask_dict['mask_file']
    mask_path = mask_dict['mask']
    mask_good = mask_dict['mask_good']
    mask_bad = mask_dict['mask_bad']
    geom_file = mask_dict['output']

    utl.copy_file(geometry, geom_file)
    
    with open(geom_file, 'r') as geo_f:
        geo_content = geo_f.readlines()

    idx_write = -1
    geo_cont_nomask = []
    # Remove all geometry 'mask*' parameters
    for i, line in enumerate(geo_content):
        if not line.lstrip().startswith("mask"):
            geo_cont_nomask.append(line)
        elif idx_write == -1:
            idx_write = i
    # Put the mask configuration after the 'dim0' key
    for i, line in enumerate(geo_cont_nomask):
        if line.lstrip().startswith("dim0"):
            idx_write = i+1
    # In case no suitable place for HD5 mask parameters have been found
    if idx_write == -1:
        idx_write = 0

    conf_mask = []
    if (idx_write > 0
        and geo_cont_nomask[idx_write-1].strip()):
        if not geo_cont_nomask[idx_write].strip():
            idx_write += 1
        else:
            conf_mask.append("\n")

    conf_mask.append("; EXtra-xwiz: config for a mask from HD5 file:\n")
    conf_mask.append(f"mask_file = {mask_file}\n")
    conf_mask.append(f"mask = {mask_path}\n")
    conf_mask.append(f"mask_good = {mask_good}\n")
    conf_mask.append(f"mask_bad = {mask_bad}\n")

    if (idx_write < len(geo_cont_nomask)
        and geo_cont_nomask[idx_write].strip()):
        conf_mask.append("\n")

    geo_cont_write = (
        geo_cont_nomask[:idx_write] + conf_mask + geo_cont_nomask[idx_write:])
    with open(geom_file, 'w') as geo_f:
        geo_f.write("".join(geo_cont_write))

    return geom_file
