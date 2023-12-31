"""
Templates for configuration and script outlines
"""

POINT_GROUPS = ['1', '2', '222', '4', '422', '3', '321', '312', '6', '622',
                '23', '432']

CONFIG = """\
[data]
proposal = 700000
runs = [30]
frames_range = {end = 100000}

[crystfel]
# Available versions: '0.8.0', '0.9.1', '0.10.2', 'maxwell_dev'
version = '0.10.2'

[geom]
file_path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/agipd_2120_v1_reform.geom"

[slurm]
# Available partitions: 'local', 'all', 'upex', 'exfel'
partition = "all"
# In case you have slurm nodes reservation
reservation = "none"
duration_all = "1:00:00"
n_nodes_all = 10

[indexamajig_run]
resolution = 4.0
peak_method = "peakfinder8"
peak_threshold = 800
peak_snr = 5
peak_min_px = 1
peak_max_px = 2
peaks_hdf5_path = "entry_1/result_1"
index_method = "mosflm"
n_cores = -1
local_bg_radius = 3
integration_radii = "2,3,5"
max_res = 1200
min_peaks = 0
extra_options = "--no-non-hits-in-stream"

[unit_cell]
file_path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/hewl.cell"
run_refine = false

[merging]
point_group = "422"
scaling_model = "unity"
scaling_iterations = 1
max_adu = 100000
"""

ADV_CONFIG = """\
[data]
proposal = 700000
runs = [30]
frames_range = {start = 0, end = -1, step = 1}
vds_names = ["p700000_r0030_vds.h5"]
cxi_names = ["p2304_r0108.cxi"]
list_prefix = "xmpl_30"
frames_list_file = "none"

[crystfel]
# Available versions: '0.8.0', '0.9.1', '0.10.2', 'cfel_dev'
version = 'cfel_dev'

[geom]
file_path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/agipd_2120_v1_reform.geom"

  [geom.add_hd5mask]
  run = false
  mask_file = "/gpfs/exfel/u/scratch/SPB/202130/p900201/lysoZn/jfBadPixelMask_03_minus2Panels_stack.h5"
  mask = "/data/data"
  mask_good = 1
  mask_bad = 0
  output = "geometry/jungfrau_p2696_v2_vds.geom"

[slurm]
# Available partitions: 'local', 'all', 'upex', 'exfel'
partition = "all"
# In case you have slurm nodes reservation
reservation = "none"
duration_all = "1:00:00"
n_nodes_all = 10
#duration_hits = "0:30:00"
#n_nodes_hits = 4

[indexamajig_run]
resolution = 4.0
peak_method = "peakfinder8"
peak_threshold = 800
peak_snr = 5
peak_min_px = 1
peak_max_px = 2
peaks_hdf5_path = "entry_1/result_1"
index_method = "mosflm"
n_cores = -1
local_bg_radius = 3
integration_radii = "2,3,5"
max_res = 1200
min_peaks = 0
extra_options = "--no-non-hits-in-stream"

[unit_cell]
file_path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/hewl.cell"
run_refine = false

[frame_filter]
match_tolerance = 0.1

[proc_fine]
execute = false
resolution = 2.0

[partialator_split]
execute = false
# Set frames from these trains to dataset 'ignore':
ignore_trains = []
# Available modes: "on_off", "on_off_numbered", "by_pulse_id", "by_train_id"
mode = "on_off"

# Required only for "on_off" or "on_off_numbered" modes:
xray_signal = ["SPB_LAS_SYS/ADC/UTC1-1:channel_0.output", "data.rawData"]
laser_signal = ["SPB_LAS_SYS/ADC/UTC1-1:channel_1.output", "data.rawData"]
plot_signal = true

# Required only for "by_pulse_id" or "by_train_id" mode:
[partialator_split.manual_datasets]
  my_on = {start=32, end=-1, step=32}
  my_off = [{start=40, step=32}, {start=48, step=32}, {start=56, step=32}]
  my_ignore = [0, 8, 16, 24]

[merging]
point_group = "422"
scaling_model = "unity"
scaling_iterations = 1
max_adu = 100000
"""

MAKE_VDS = """\
#!/bin/sh

extra-data-make-virtual-cxi \\
  %(DATA_PATH)s \\
  -o %(VDS_NAME)s \\
  --fill-value data 0.0 \\
  --fill-value mask %(MASK_BAD)s
"""

PROC_VDS_BASH_SLURM = """\
#!/bin/sh
unset LD_PRELOAD
source /etc/profile.d/modules.sh
module purge

module load ccp4/7.0
%(IMPORT_CRYSTFEL)s

NODE="$(srun hostname)"
TIMELIMIT="$(squeue -j $SLURM_JOB_ID -o '%%l' | tail -1)"

echo "LOG: Job started at $NODE with the time limit of $TIMELIMIT."
echo "LOG: start on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
echo ""
indexamajig --version
echo ""
N_CORES_USE=%(CORES)s
N_CORES_AVAL="$(nproc)"
if [ $N_CORES_USE -lt 0 ]
then
  N_CORES_USE=$N_CORES_AVAL
fi
echo "LOG: Using $N_CORES_USE out of $N_CORES_AVAL available cores."
echo ""

indexamajig \\
  -i %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.lst \\
  -o %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.stream \\
  -g %(GEOM)s %(CRYSTAL)s \\
  -j $N_CORES_USE \\
  --highres=%(RESOLUTION)s \\
  --peaks=%(PEAK_METHOD)s \\
  --min-snr=%(PEAK_SNR)s \\
  --threshold=%(PEAK_THRESHOLD)s \\
  --min-pix-count=%(PEAK_MIN_PX)s \\
  --max-pix-count=%(PEAK_MAX_PX)s \\
  --indexing=%(INDEX_METHOD)s \\
  --int-radius=%(INT_RADII)s \\
  --local-bg-radius=%(LOCAL_BG_RADIUS)s \\
  --max-res=%(MAX_RES)s \\
  --min-peaks=%(MIN_PEAKS)s \\
%(COPY_FIELDS)s  %(EXTRA_OPTIONS)s %(HARVEST_OPTION)s

echo ""
echo "LOG: finished on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
"""


PROC_VDS_BASH_LOCAL = """\
#!/bin/sh

%(IMPORT_CRYSTFEL)s

echo "LOG: start on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
echo ""
indexamajig --version
echo ""
N_CORES_USE=%(CORES)s
N_CORES_AVAL="$(nproc)"
if [ $N_CORES_USE -lt 0 ]
then
  N_CORES_USE=$N_CORES_AVAL
fi
echo "LOG: Using $N_CORES_USE out of $N_CORES_AVAL available cores."
echo ""

indexamajig \\
  -i %(PREFIX)s_0.lst \\
  -o %(PREFIX)s_0.stream \\
  -g %(GEOM)s %(CRYSTAL)s \\
  -j $N_CORES_USE \\
  --highres=%(RESOLUTION)s \\
  --peaks=%(PEAK_METHOD)s \\
  --min-snr=%(PEAK_SNR)s \\
  --threshold=%(PEAK_THRESHOLD)s \\
  --min-pix-count=%(PEAK_MIN_PX)s \\
  --max-pix-count=%(PEAK_MAX_PX)s \\
  --indexing=%(INDEX_METHOD)s \\
  --int-radius=%(INT_RADII)s \\
  --local-bg-radius=%(LOCAL_BG_RADIUS)s \\
  --max-res=%(MAX_RES)s \\
  --min-peaks=%(MIN_PEAKS)s \\
%(COPY_FIELDS)s  %(EXTRA_OPTIONS)s %(HARVEST_OPTION)s

echo ""
echo "LOG: finished on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
"""


PROC_CXI_BASH_SLURM = """\
#!/bin/sh
unset LD_PRELOAD
source /etc/profile.d/modules.sh
module purge

module load ccp4/7.0
%(IMPORT_CRYSTFEL)s

NODE="$(srun hostname)"
TIMELIMIT="$(squeue -j $SLURM_JOB_ID -o '%%l' | tail -1)"

echo "LOG: Job started at $NODE with the time limit of $TIMELIMIT."
echo "LOG: start on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
echo ""
indexamajig --version
echo ""
N_CORES_USE=%(CORES)s
N_CORES_AVAL="$(nproc)"
if [ $N_CORES_USE -lt 0 ]
then
  N_CORES_USE=$N_CORES_AVAL
fi
echo "LOG: Using $N_CORES_USE out of $N_CORES_AVAL available cores."
echo ""

indexamajig \\
  -i %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.lst \\
  -o %(PREFIX)s_${SLURM_ARRAY_TASK_ID}.stream \\
  -g %(GEOM)s %(CRYSTAL)s \\
  -j $N_CORES_USE \\
  --highres=%(RESOLUTION)s \\
  --peaks=cxi \\
  --hdf5-peaks=%(PEAKS_HDF5_PATH)s \\
  --indexing=%(INDEX_METHOD)s \\
%(COPY_FIELDS)s  %(EXTRA_OPTIONS)s %(HARVEST_OPTION)s

echo ""
echo "LOG: finished on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
"""

PARTIALATOR_WRAP = """\
#!/bin/sh

%(IMPORT_CRYSTFEL)s

partialator \\
    -i %(PREFIX)s_hits.stream \\
    -o %(PREFIX)s_merged.hkl \\
    -y %(POINT_GROUP)s \\
    --max-adu=%(MAX_ADU)s \\
    --iterations=%(N_ITER)s \\
    --model=%(MODEL)s \\
    %(PARTIALATOR_SPLIT)s
"""

CHECK_HKL_WRAP = """\
#!/bin/sh

%(IMPORT_CRYSTFEL)s

check_hkl \\
    %(PREFIX)s_merged%(DS_SUFFIX)s.hkl \\
    -y %(POINT_GROUP)s \\
    -p %(UNIT_CELL)s \\
    --highres=%(HIGH_RES)s \\
    --shell-file=%(PREFIX)s_completeness%(DS_SUFFIX)s.dat
"""

COMPARE_HKL_WRAP = """\
#!/bin/sh

%(IMPORT_CRYSTFEL)s

compare_hkl \\
    %(PREFIX)s_merged%(DS_SUFFIX)s.hkl1 \\
    %(PREFIX)s_merged%(DS_SUFFIX)s.hkl2 \\
    -y %(POINT_GROUP)s \\
    -p %(UNIT_CELL)s \\
    --highres=%(HIGH_RES)s \\
    --fom=%(FOM)s \\
    --shell-file=%(PREFIX)s_%(FOM)s%(DS_SUFFIX)s.dat
"""

CELL_EXPLORER_WRAP = """\
#!/bin/sh

%(IMPORT_CRYSTFEL)s

cell_explorer %(PREFIX)s.stream
"""

HDFSEE_WRAP = """\
#!/bin/sh

%(IMPORT_CRYSTFEL)s

hdfsee %(DATA_FILE)s -g %(GEOM)s
"""
