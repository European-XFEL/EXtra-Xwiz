"""Exceptions for mask convertor."""


class MaskConvError(Exception):

    # List all known exception types (for bookkeeping):
    mask_err_types = [
        # In case of unexpected exception type:
        'unknown',

        # During initialization of MaskConverter:
        'conv_init_wrong_mode',         # Wrong run or write mode
        'conv_init_unknown_detector',   # Missing detector info in
                                        # detector_info.py
        'conv_init_missing_data_type',  # Missing data type for detector
                                        # in detector_info.py

        # While trying to guess missing detector info:
        'cannot_guess_detector_info',   # Could not make an educated
                                        # guess

        # While reading input from HDF5:
        'read_hd5_cannot_access_file',  # Cannot read HD5 file
        'read_hd5_wrong_path',          # Wrong path to the mask in HDF5
        'read_hd5_wrong_entry_number',  # Mask entry outside of range
        'read_hd5_wrong_mask_shape',    # Shape of the mask in HD5 file
                                        # does not correspond to the
                                        # data in detector_info.py

        # While reading input from geomentry file:
        'read_geo_no_file',             # Cannot read geometry file
        'read_geo_wrong_panel',         # Unexpected or not suitable
                                        # panel/asic description

        # While writing to the HD5 file:
        'write_hd5_no_permission',      # HD5 file already exists but
                                        # there is no write permission

        # While writing to the geometry file:
        'write_geo_no_permission'       # Geometry file exists but
                                        # there is no write permission
    ]

    def __init__(self, message, err_type):
        self.message = message
        if err_type in type(self).mask_err_types:
            self.err_type = err_type
        else:
            raise MaskConvError(
                f"Unknown exception type: {message}",
                'unknown')

    def __srt__(self):
        return self.message

    @staticmethod
    def check_hd5mask(hd5mask, mask_shape, mask_entry):
        """
        Static method to check dimensions of the mask in HD5 file.
            Input:
                hd5mask     - mask from the HD5 file
                mask_shape  - expected shape of the mask
                mask_entry  - mask entry of interest
        """

        # Check the HDF5 mask shape
        if (hd5mask.shape[-len(mask_shape):] != mask_shape
                or hd5mask.ndim > (len(mask_shape) + 1)):
            raise MaskConvError(
                f"ERROR: Wrong mask shape in HD5 file: {hd5mask.shape}; "
                f"expected: {mask_shape} or {('n_data', *mask_shape)}.",
                'read_hd5_wrong_mask_shape')

        # Check the mask entry range
        if hd5mask.ndim > len(mask_shape):
            max_entry = hd5mask.shape[0] - 1
        else:
            max_entry = 0
        if mask_entry > max_entry:
            raise MaskConvError(
                f"ERROR: In HD5 file mask entry {mask_entry} "
                f"outside of range (0,{max_entry}).",
                'read_hd5_wrong_entry_number')
