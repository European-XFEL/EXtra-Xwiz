"""
Functions to parse the relevant detector geometry from a file
"""

def get_detector_distance(fn):
    """ Read the sample-to-detector distance (aka "camera length")
    """
    with open(fn) as f:
        for ln in f:
            if ln[:6] == 'clen =':
                return ln.split()[-1]
        print(' Warning: "clen" keyword not found')
        return '0.9999'

def get_photon_energy(fn):
    """ Read the photon energy (equivalent to wavelength)
    """
    with open(fn) as f:
        for ln in f:
            if ln[:15] == 'photon_energy =':
                return ln.split()[-1]
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


