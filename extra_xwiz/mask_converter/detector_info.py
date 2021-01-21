"""Module with a dictionary containing detectors information."""

# Third party imports
import numpy as np


detector_info = {
    'Jungfrau': {
        'VDS': {
            'shape': (8, 512, 1024),

            # Masked region -> True
            'read_mask': lambda X: (X > 0),
            'write_mask': lambda X: (X.astype(int)),

            'panel_names': ['p1', 'p2', 'p3', 'p4',
                            'p5', 'p6', 'p7', 'p8'],

            'asic_names': ['a1', 'a2', 'a3', 'a4',
                           'a5', 'a6', 'a7', 'a8'],

            'asic_range': [[                          # for panels 1-4
                (slice(256, 512), slice(768, 1024)),  # asic 1
                (slice(256, 512), slice(512,  768)),  # asic 2
                (slice(256, 512), slice(256,  512)),  # ...
                (slice(256, 512), slice(  0,  256)),
                (slice(  0, 256), slice(768, 1024)),
                (slice(  0, 256), slice(512,  768)),
                (slice(  0, 256), slice(256,  512)),
                (slice(  0, 256), slice(  0,  256))
            ]]*4 + [[                                 # for panels 5-8
                (slice(  0, 256), slice(  0,  256)),  # asic 1
                (slice(  0, 256), slice(256,  512)),  # asic 2
                (slice(  0, 256), slice(512,  768)),  # ...
                (slice(  0, 256), slice(768, 1024)),
                (slice(256, 512), slice(  0,  256)),
                (slice(256, 512), slice(256,  512)),
                (slice(256, 512), slice(512,  768)),
                (slice(256, 512), slice(768, 1024))
            ]]*4
        },

        'Cheetah': {
            'shape': (4096, 1024),

            # Masked region -> True
            'read_mask': lambda X: (X == 0),
            'write_mask': lambda X: (np.logical_not(X).astype(int))
        }
    },

    'AGIPD': {
        'VDS': {
            'shape': (16, 512, 128),

            # Masked region -> True
            'read_mask': lambda X: (X > 0),
            'write_mask': lambda X: (X.astype(int)),

            'panel_names': ['p0',  'p1',  'p2',  'p3',
                            'p4',  'p5',  'p6',  'p7',
                            'p8',  'p9',  'p10', 'p11',
                            'p12', 'p13', 'p14', 'p15'],

            'asic_names': ['a0', 'a1', 'a2', 'a3',
                           'a4', 'a5', 'a6', 'a7'],

            'asic_range': [[                        # same for 16 panels
                (slice(  0,  64), slice(0, 128)),   # asic 1
                (slice( 64, 128), slice(0, 128)),   # asic 2
                (slice(128, 192), slice(0, 128)),   # ...
                (slice(192, 256), slice(0, 128)),
                (slice(256, 320), slice(0, 128)),
                (slice(320, 384), slice(0, 128)),
                (slice(384, 448), slice(0, 128)),
                (slice(448, 512), slice(0, 128))
            ]]*16
        },

        'Cheetah': {
            'shape': (8192, 128),

            # Masked region -> True
            'read_mask': lambda X: (X == 0),
            'write_mask': lambda X: (np.logical_not(X).astype(int))
        }
    }
}


def get_data_types(detector_names=None):
    """
    Prepare a list with all data types available in detector_info
    for <detector_names>.
    """

    if detector_names is not None:
        detectors = detector_names
    else:
        detectors = list(detector_info.keys())

    data_types = []
    for detector in detectors:
        for data_type in detector_info[detector].keys():
            if data_type not in data_types:
                data_types.append(data_type)

    return data_types
