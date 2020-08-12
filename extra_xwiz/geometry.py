"""
Functions to parse the relevant detector geometry from a file
"""

import warnings

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
    with open(fn) as f:
        for ln in f:
            if ln[:10] == 'mask_bad =':
                return ln.split()[-1]
        print(' Warning: "mask_bad" keyword not found')
        return '0xffff'


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


