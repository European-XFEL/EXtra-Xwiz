"""
Module with a dictionary containing version-specific CrystFEL
information.
"""

FRAMES_PATTERN_9 = r'(^|Final:)(\s?\d*\s)(images)'
CRYSTALS_PATTERN_8 = r'(\),\s*)(\d*)( crystals)'

crystfel_info = {
    '0.8.0': {
        'import':
            'source /usr/share/Modules/init/sh\n'
            'module load exfel\n'
            'module load spack\n'
            'spack load crystfel@0.8.0',
        'log_frames_pattern':
            r'(\s*\d*.indexable out of |Final:)(\s?\d*\s)(p|i)',
        'log_crystals_pattern':
            CRYSTALS_PATTERN_8,
        'contain_harvest': False,
    },

    '0.9.1': {
        'import':
            'source /usr/share/Modules/init/sh\n'
            'module load maxwell crystfel/0.9.1',
        'log_frames_pattern':
            FRAMES_PATTERN_9,
        'log_crystals_pattern':
            CRYSTALS_PATTERN_8,
        'contain_harvest': False,
    },

    '0.10.2': {
        'import':
            'source /usr/share/Modules/init/sh\n'
            'module load maxwell crystfel/0.10.2',
        'log_frames_pattern':
            FRAMES_PATTERN_9,
        'log_crystals_pattern':
            CRYSTALS_PATTERN_8,
        'contain_harvest': True,
    },

    '0.10.2_visa': {
        'import':
            '',
        'log_frames_pattern':
            FRAMES_PATTERN_9,
        'log_crystals_pattern':
            CRYSTALS_PATTERN_8,
        'contain_harvest': True,
    },

    'cfel_dev': {
        'import':
            'export PATH='
            '/gpfs/cfel/group/cxi/common/public/development/crystfel/bin:$PATH',
        'log_frames_pattern':
            FRAMES_PATTERN_9,
        'log_crystals_pattern':
            CRYSTALS_PATTERN_8,
        'contain_harvest': True,
    },

    'maxwell_dev': {
        'import':
            'module load maxwell crystfel/0-devel',
        'log_frames_pattern':
            FRAMES_PATTERN_9,
        'log_crystals_pattern':
            CRYSTALS_PATTERN_8,
        'contain_harvest': True,
    },
}
