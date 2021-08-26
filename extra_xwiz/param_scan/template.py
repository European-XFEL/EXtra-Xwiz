
CONFIG_TEMPLATE = """\
[settings]

xwiz_config = '/gpfs/exfel/data/user/turkot/LWork/Xwiz/merged/dev_copy_h5_fields/r_02/xwiz_conf.toml'
log_completion = 20

[xwiz]
path_parameters = [
    'data.path',
    'data.vds_names',
    'geom.file_path',
    'geom.add_hd5mask.mask_file',
    'geom.add_hd5mask.output',
    'unit_cell.file',
    'some.crazy.path'
]


[scan.run]
  'data.runs' = ['35', '36', '37']
  'data.vds_names' = [
      'jf_p002697_35_vds.cxi',
      'jf_p002697_36_vds.cxi',
      'jf_p002697_37_vds.cxi'
  ]

[scan.SNR]
  'proc_coarse.peak_snr' = {start = 3, end = 7, step = 2}

[output.store_xarray]
  output_file = "scan_data.nc"

[output.store_csv]
  output_file = "scan_data.csv"
"""
