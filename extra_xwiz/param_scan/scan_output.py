import re

import xarray as xr

def get_xwiz_index_rate(summary_file: str) -> float:
    index_rate_re = re.compile(r"OVERALL\s+\d+\s+\d+\s+(\d+\.?\d*)")
    with open(summary_file, 'r') as sumfile:
        for line in sumfile:
            mobj = re.search(index_rate_re, line)
            if mobj is not None:
                return float(mobj.group(1))
        # Explicit is better than implicit
        return None

def output_processors(processor_func):
    output_processors.dict = getattr(output_processors, 'dict', dict())
    output_processors.dict[processor_func.__name__] = processor_func

@output_processors
def store_xarray(scan_data: xr.DataArray, output_file: str):
    scan_data.to_netcdf(output_file)

@output_processors
def store_csv(scan_data: xr.DataArray, output_file: str):
    scan_series = scan_data.to_series()
    scan_series.name = scan_data.attrs['long_name']
    scan_series.to_csv(output_file, na_rep='NaN')
