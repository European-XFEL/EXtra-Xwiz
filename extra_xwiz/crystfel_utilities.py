"""Module for utility functions related to running CrystFEL."""

import os.path as osp
import re

def get_n_crystals(stream_file: str) -> int:
    """Get a number of crystals from the stream file."""
    if osp.exists(stream_file):
        n_cryst = len(
            re.findall('Cell parameters', open(stream_file).read())
        )
    else:
        n_cryst = None
    return n_cryst

def get_n_hits(stream_file: str, min_peaks: int) -> int:
    """Get a number of frames with at least 'min_peaks' peaks."""
    if osp.exists(stream_file):
        re_peaks = r'num_peaks = (\d+)'
        n_peaks = [
            int(val) for val in re.findall(re_peaks, open(stream_file).read())]
        n_hits = len([val for val in n_peaks if val >= min_peaks])
    else:
        n_peaks = None
    return n_hits
