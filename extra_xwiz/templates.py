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
time = "3:00:00"
n_nodes = 4

[proc_coarse]
resolution = 4.0
peaks = "peakfinder8"
indexing = "mosflm"
cell = "hewl.cell"
n_cores = 20

[proc_fine]
resolution = 2.0
peaks = "peakfinder8"
indexing = "mosflm"
# cell is expected to be 
n_cores = 20
"""

PROC_BASH = """\
#!/bin/bash

indexamajig \\
  -i %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.lst \\
  -o %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.stream \\
  -g %(GEOM)s %(SYMM)s \\
  --peaks=%(PEAKS)s %(PEAKOPTS)s \\
  --indexing=%(INDEXING)s \\
  -j %(CORES)s
"""

