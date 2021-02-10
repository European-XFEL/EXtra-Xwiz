"""
Utility functions for the mask converter.
"""


def check_hd5mask(hd5mask, mask_shape, mask_entry):
    """
    Function to check dimensions of the mask from HD5 file.

    Args:
        hd5mask (2D np.array, dtype=bool): mask read from the HD5 file.
        mask_shape (tuple): expected shape of the mask.
        mask_entry (int): entry number of the mask in HD5 file.

    Raises:
        ValueError: shape of the hd5mask does not correspond to the
            mask_shape.
        IndexError: mask_entry outside of hd5mask entries range.
    """

    # Check the HDF5 mask shape
    if (hd5mask.shape[-len(mask_shape):] != mask_shape
            or hd5mask.ndim > (len(mask_shape) + 1)):
        raise ValueError(
            f"Wrong mask shape in HD5 file: {hd5mask.shape}; "
            f"expected: {mask_shape} or {('n_data', *mask_shape)}.")

    # Check the mask entry range
    if hd5mask.ndim > len(mask_shape):
        max_entry = hd5mask.shape[0] - 1
    else:
        max_entry = 0
    if mask_entry > max_entry:
        raise IndexError(
            f"In HD5 file mask entry {mask_entry} outside of range "
            f"(0,{max_entry}).")


def rect2dict(rect, panel):
    """
    Help function to turn decomposition algorithm output into a dictionary
    of rectangles (in the same format as in the geometry file).

    Args:
        rect (list): list of rectangles that represent masked regionsin
            in the form: [((x_min, x_max),(y_min, y_max)), ...].
        panel (string): name of the detector panel.

    Returns:
        dict: dictionary of rectangles (in the same format as in the
            geometry file)
    """
    d = {}
    rect2dict.n_area = getattr(rect2dict, 'n_area', -1)
    for rec in rect:
        rect2dict.n_area += 1
        d[rect2dict.n_area] = {
            'min_fs': rec[0][0],
            'max_fs': rec[0][1] - 1,  # Mask range is inclusive
            'min_ss': rec[1][0],
            'max_ss': rec[1][1] - 1,  # Mask range is inclusive
            'panel': panel
        }
    return d
