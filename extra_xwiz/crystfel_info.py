"""
Module with a dictionary containing version-specific CrystFEL
information.
"""


crystfel_info = {
    '0.8.0': {
        'log_frames_pattern':
            r'(\s*\d*.indexable out of |Final:)(\s?\d*\s)(p|i)',
        'log_crystals_pattern':
            r'(\),\s*)(\d*)( crystals)',
    },

    '0.9.1': {
        'log_frames_pattern':
            r'(^|Final:)(\s?\d*\s)(images)',
        'log_crystals_pattern':
            r'(\),\s*)(\d*)( crystals)',
    },
}
