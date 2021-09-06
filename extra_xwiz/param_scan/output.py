import os.path as osp
import re
from typing import Callable

import numpy as np
import xarray as xr

# List of xwiz foms, their type and regular expressions in xwiz summary
FOMS = {
    "index_rate": {
        "reg_exp": r"OVERALL\s+\d+\s+\d+\s+(\d+\.?\d*)",
        "type": np.float32
    },
    "n_crystals": {
        "reg_exp": r"OVERALL\s+(\d+)",
        "type": np.int32
    },
    "n_frames": {
        "reg_exp": r"OVERALL\s+\d+\s+(\d+)",
        "type": np.int32
    },
    "completeness": {
        "reg_exp": r"Completeness\s+(\d+\.?\d*)",
        "type": np.float32
    },
    "snr": {
        "reg_exp": r"Signal-over-noise\s+(\d+\.?\d*)",
        "type": np.float32
    },
    "cc_half": {
        "reg_exp": r"CC_1/2\s+(\d+\.?\d*)",
        "type": np.float32
    },
    "cc_star": {
        "reg_exp": r"CC\*\s+(\d+\.?\d*)",
        "type": np.float32
    },
    "r_split": {
        "reg_exp": r"R_split\s+(\d+\.?\d*)",
        "type": np.float32
    },
}

def get_xwiz_foms(summary_file: str) -> dict:
    """Read figures of merit from the xwiz summary file.

    Parameters
    ----------
    summary_file : str
        Path to the xwiz summary file.

    Returns
    -------
    dict
        Dictionary of foms read from the xwiz summary file.
    """
    xwiz_foms = {}
    if (osp.exists(summary_file)):
        with open(summary_file, 'r') as sumfile:
            for line in sumfile:
                for fom in FOMS:
                    m_line = line
                    mobj = re.search(FOMS[fom]['reg_exp'], m_line)
                    if mobj is not None:
                        xwiz_foms[fom] = FOMS[fom]['type'](mobj.group(1))
    return xwiz_foms


def output_processors(processor: Callable) -> Callable:
    """"Decorator for parameters scanner output processing functions
    which stores them in an output_processors.dict dictionary.

    Parameters
    ----------
    processor : Callable
        Parameters scanner output processing function.

    Returns
    -------
    Callable
        Unmodified output processing function.
    """
    output_processors.dict = getattr(output_processors, 'dict', dict())
    output_processors.dict[processor.__name__] = processor
    return processor


@output_processors
def store_xarray(scan_data: xr.Dataset, output_file: str) -> None:
    """Store parameters scanner output as a netCDF file.

    Parameters
    ----------
    scan_data : xr.Dataset
        Dataset with parameters scanner output - xwiz figures of merit
        for all finished scan jobs.
    output_file : str
        Path to the netCDF output file.
    """
    scan_data.to_netcdf(output_file)


@output_processors
def store_csv(scan_data: xr.Dataset, output_file: str) -> None:
    """Store parameters scanner output as a CSV file.

    Parameters
    ----------
    scan_data : xr.Dataset
        Dataset with parameters scanner output - xwiz figures of merit
        for all finished scan jobs.
    output_file : str
        Path to the CSV output file.
    """
    scan_series = scan_data.to_dataframe()
    scan_series.to_csv(output_file, na_rep='NaN')
