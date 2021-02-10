"""
Internal module with a function for rectangular decomposition
of binary images based on paper:
http://library.utia.cas.cz/separaty/2012/ZOI
/suk-rectangular%20decomposition%20of%20binary%20images.pdf
"""

# Third party imports
import numpy as np


def delta_method(mask):
    """
    Generalized delta-method algorithm to decompose two-dimensional mask
    (boolean numpy array) into rectangles.

    Args:
        mask (2D np.array, dtype=bool): input mask.

    Raises:
        ValueError: mask is not a 2D boolean numpy array.

    Returns:
        list: list of rectangles that represent masked regionsin in the form:
            [((x_min, x_max),(y_min, y_max)), ...]
    """

    # Check input:
    if (mask.ndim != 2
            or mask.dtype != bool):
        raise ValueError(f"Expected input - 2D boolean numpy array.")

    A = np.copy(mask)
    res = []

    i_y = 0
    while not np.array_equiv(A, False):

        assert i_y < A.shape[0], (
            "Decomposition GDM: algorithm did not convert the whole matrix.")

        x_min = x_max = y_min = y_max = -1
        for i_x in range(A.shape[1]):
            if x_min < 0 and A[i_y, i_x]:
                x_min = i_x
                y_min = i_y
                if i_x == A.shape[1] - 1:
                    x_max = A.shape[1]
            elif x_min >= 0 and not A[i_y, i_x]:
                x_max = i_x
            elif x_min >= 0 and i_x == A.shape[1] - 1:
                x_max = A.shape[1]

            if x_max >= 0:
                sx = slice(x_min, x_max)
                for i_y2 in range(i_y + 1, A.shape[0]):
                    if not np.array_equal(A[i_y2, sx], A[i_y, sx]):
                        y_max = i_y2
                        break
                else:
                    y_max = A.shape[0]
                res.append(((x_min, x_max), (y_min, y_max)))
                A[y_min:y_max, sx] = False
                x_min = x_max = y_min = y_max = -1

        i_y += 1

    return res
