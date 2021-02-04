"""
Internal module with functions for rectangular decomposition
of binary images based on paper:
http://library.utia.cas.cz/separaty/2012/ZOI
/suk-rectangular%20decomposition%20of%20binary%20images.pdf
"""

# Third party imports
import numpy as np


def gdm(A_inp):
    """
    Generalized delta-method algorithm to decompose binary image
    (numpy array) into rectangles.
        Input:
            Ainp - two-dimensional boolean numpy array.
        Output:
            List of rectangles - [((x_min, x_max),(y_min, y_max)), ...]
    """
    # Check input:
    if A_inp.ndim != 2:
        raise ValueError(f"Dimension mismatch - {A_inp.ndim}, expected 2.")

    A = np.copy(A_inp)
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
