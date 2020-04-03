"""
Templates for configuration and script outlines
"""

CONFIG = """\
[data]
path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0002"
n_frames = 40000
vds_name = "xmpl_2_vds.cxi"
list_prefix = "xmpl_2_frames"
geometry = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0002/agipd_mar18_v22.geom"

[slurm]
partition = "exfel"
duration = "3:00:00"
n_nodes = 4

[proc_coarse]
resolution = 4.0
peak_method = "peakfinder8"
peak_threshold = 800
peak_snr = 5
index_method = "mosflm"
unit_cell = "hewl.cell"
n_cores = 20

[proc_fine]
resolution = 2.0
"""

PROC_BASH = """\
#!/bin/bash

indexamajig \\
  -i %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.lst \\
  -o %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.stream \\
  -g %(GEOM)s %(SYMM)s \\
  -j %(CORES)s \\
  --highres=%(RESOLUTION)s \\
  --peaks=%(PEAK_METHOD)s \\
  --min-snr=%(MIB)s \\
  --threshold=%(PEAK_THRESHOLD)s \\
  --indexing=%(INDEX_METHOD)s \\
  --no-non-hits-in-stream  
"""

