import os.path as osp
import re

import xarray as xr

#List of xwiz foms and their regular expressions in the summary file
FOMS = {
    "index_rate": {
        "reg_exp": r"OVERALL\s+\d+\s+\d+\s+(\d+\.?\d*)",
        "type": float
    },
    "n_crystals": {
        "reg_exp": r"OVERALL\s+(\d+)",
        "type": int
    },
    "n_frames": {
        "reg_exp": r"OVERALL\s+\d+\s+(\d+)",
        "type": int
    },
    "completeness": {
        "reg_exp": r"Completeness\s+(\d+\.?\d*)",
        "type": float
    },
    "snr": {
        "reg_exp": r"Signal-over-noise\s+(\d+\.?\d*)",
        "type": float
    },
    "cc_half": {
        "reg_exp": r"CC_1/2\s+(\d+\.?\d*)",
        "type": float
    },
    "cc_star": {
        "reg_exp": r"CC\*\s+(\d+\.?\d*)",
        "type": float
    },
    "r_split": {
        "reg_exp": r"R_split\s+(\d+\.?\d*)",
        "type": float
    },
}

def get_xwiz_foms(summary_file: str) -> dict:
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


def output_processors(processor_func):
    output_processors.dict = getattr(output_processors, 'dict', dict())
    output_processors.dict[processor_func.__name__] = processor_func


@output_processors
def store_xarray(scan_data: xr.Dataset, output_file: str):
    scan_data.to_netcdf(output_file)


@output_processors
def store_csv(scan_data: xr.Dataset, output_file: str):
    scan_series = scan_data.to_dataframe()
    scan_series.to_csv(output_file, na_rep='NaN')
