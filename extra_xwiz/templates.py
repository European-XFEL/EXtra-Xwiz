"""
Templates for configuration and script outlines
"""

POINT_GROUPS = ['1', '2', '222', '4', '422', '3', '321', '312', '6', '622',
                '23', '432']

CONFIG = """\
[data]
path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0028"
n_frames = 200000
vds_name = "xmpl_28_vds.cxi"
list_prefix = "xmpl_28_frames"
geometry = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0028/agipd_2450_vds_v4.geom"

[slurm]
partition = "exfel"
duration = "1:00:00"
n_nodes = 10

[proc_coarse]
resolution = 4.0
peak_method = "peakfinder8"
peak_threshold = 800
peak_snr = 5
peak_min_px = 1 
index_method = "mosflm"
unit_cell = "hewl.cell"
n_cores = 40

[proc_fine]
resolution = 2.0
integration_radii = "2,3,5"

[merging]
point_group = "422"
scaling_model = "unity"
scaling_iterations = 1
max_adu = 100000
"""

PROC_BASH_SLURM = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel 
module load spack
spack load crystfel
module load ccp4/7.0

indexamajig \\
  -i %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.lst \\
  -o %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.stream \\
  -g %(GEOM)s %(CRYSTAL)s \\
  -j %(CORES)s \\
  --highres=%(RESOLUTION)s \\
  --peaks=%(PEAK_METHOD)s \\
  --min-snr=%(PEAK_SNR)s \\
  --threshold=%(PEAK_THRESHOLD)s \\
  --min-pix-count=%(PEAK_MIN_PX)s \\
  --indexing=%(INDEX_METHOD)s \\
  --no-non-hits-in-stream  
"""

PROC_BASH_DIRECT = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel 
module load spack
spack load crystfel
module load ccp4/7.0

indexamajig \\
  -i %(PREFIX)s_hits.lst \\
  -o %(PREFIX)s_hits.stream \\
  -g %(GEOM)s \\
  %(CRYSTAL)s \\
  -j %(CORES)s \\
  --highres=%(RESOLUTION)s \\
  --peaks=%(PEAK_METHOD)s \\
  --min-snr=%(PEAK_SNR)s \\
  --threshold=%(PEAK_THRESHOLD)s \\
  --min-pix-count=%(PEAK_MIN_PX)s \\
  --indexing=%(INDEX_METHOD)s \\
  --no-non-hits-in-stream \\
  --int-radius=%(INT_RADII)s
"""

PARTIALATOR_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel
module load spack
spack load crystfel

partialator \\
    -i %(PREFIX)s_hits.stream \\
    -o %(PREFIX)s_merged.hkl \\
    -y %(POINT_GROUP)s \\
    --max-adu=%(MAX_ADU)s \\
    --iterations=%(N_ITER)s \\
    --model=%(MODEL)s
"""

CHECK_HKL_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel
module load spack
spack load crystfel

check_hkl \\
    %(PREFIX)s_merged.hkl \\
    -y %(POINT_GROUP)s \\
    -p %(UNIT_CELL)s \\
    --highres=%(HIGH_RES)s \\
    --shell-file=%(PREFIX)s_completeness.dat
"""

COMPARE_HKL_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh
module load exfel
module load spack
spack load crystfel

compare_hkl \\
    %(PREFIX)s_merged.hkl1 \\
    %(PREFIX)s_merged.hkl2 \\
    -y %(POINT_GROUP)s \\
    -p %(UNIT_CELL)s \\
    --highres=%(HIGH_RES)s \\
    --fom=%(FOM)s \\
    --shell-file=%(PREFIX)s_%(FOM_TAG)s.dat
"""

CELL_EXPLORER_WRAP = """\
source /usr/share/Modules/init/sh
module load exfel
module load spack
spack load crystfel

cell_explorer %(PREFIX)s.stream
"""
