"""
Templates for configuration and script outlines
"""

POINT_GROUPS = ['1', '2', '222', '4', '422', '3', '321', '312', '6', '622',
                '23', '432']

CONFIG = """\
[data]
path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/"
runs = "30"
n_frames = 100000
frame_offset = 0
vds_names = "xmpl_30_vds.cxi"
vds_mask_bad = "0xffff"
cxi_names = "p2304_r0108.cxi"
list_prefix = "xmpl_30"

[crystfel]
version = '0.8.0'

[geom]
file_path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/agipd_2120_v1_reform.geom"
template_path = "./agipd_mar18_v11.geom"

[slurm]
partition = "exfel"
duration_all = "1:00:00"
n_nodes_all = 10
duration_hits = "0:30:00"
n_nodes_hits = 4

[proc_coarse]
resolution = 4.0
peak_method = "peakfinder8"
peak_threshold = 800
peak_snr = 5
peak_min_px = 1
peaks_hdf5_path = "entry_1/result_1"
index_method = "mosflm"
unit_cell = "hewl.cell"
n_cores = 40

[frame_filter]
match_tolerance = 0.1

[proc_fine]
resolution = 2.0
integration_radii = "2,3,5"

[merging]
point_group = "422"
scaling_model = "unity"
scaling_iterations = 1
max_adu = 100000
"""

MAKE_VDS = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel
module load exfel_anaconda3/1.1

extra-data-make-virtual-cxi \\
  %(DATA_PATH)s \\
  -o %(VDS_NAME)s \\
  --fill-value data 0.0 \\
  --fill-value mask %(MASK_BAD)s
"""

PROC_VDS_BASH_SLURM = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load ccp4/7.0
module load exfel
module load spack
spack load crystfel@%(CRYSTFEL_VER)s

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
  --copy-hdf5-field=/entry_1/pulseId \\
  --copy-hdf5-field=/entry_1/trainId \\
  --no-non-hits-in-stream \\
  --int-radius=%(INT_RADII)s
"""

PROC_CXI_BASH_SLURM = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load ccp4/7.0
module load exfel
module load spack
spack load crystfel@%(CRYSTFEL_VER)s

indexamajig \\
  -i %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.lst \\
  -o %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.stream \\
  -g %(GEOM)s %(CRYSTAL)s \\
  -j %(CORES)s \\
  --highres=%(RESOLUTION)s \\
  --peaks=cxi \\
  --hdf5-peaks=%(PEAKS_HDF5_PATH)s \\
  --indexing=%(INDEX_METHOD)s \\
  --copy-hdf5-field=/instrument/pulseID \\
  --copy-hdf5-field=/instrument/trainID \\
  --no-non-hits-in-stream
"""

PARTIALATOR_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel
module load spack
spack load crystfel@%(CRYSTFEL_VER)s

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
spack load crystfel@%(CRYSTFEL_VER)s

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
spack load crystfel@%(CRYSTFEL_VER)s

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
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel
module load spack
spack load crystfel@%(CRYSTFEL_VER)s

cell_explorer %(PREFIX)s.stream
"""

HDFSEE_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh

module load exfel
module load spack
spack load crystfel@%(CRYSTFEL_VER)s

hdfsee %(DATA_FILE)s -g %(GEOM)s
"""

