"""
Templates for configuration and script outlines
"""

POINT_GROUPS = ['1', '2', '222', '4', '422', '3', '321', '312', '6', '622',
                '23', '432']

CONFIG = """\
[data]
proposal = 700000
runs = [30]
n_frames_total = 100000
vds_names = ["xmpl_30_vds.cxi"]
list_prefix = "xmpl_30"

[crystfel]
# Available versions: '0.8.0', '0.9.1', '0.10.1','cfel_dev'
version = 'cfel_dev'

[geom]
file_path = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/agipd_2120_v1_reform.geom"

[slurm]
# Available partitions: 'all', 'upex', 'exfel'
partition = "all"
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
peak_max_px = 2
peaks_hdf5_path = "entry_1/result_1"
index_method = "mosflm"
n_cores = -1
local_bg_radius = 3
max_res = 1200
min_peaks = 0
extra_options = "--no-non-hits-in-stream"

[unit_cell]
file = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/hewl.cell"
run_refine = false

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

ADV_CONFIG = """\
[data]
proposal = 700000
runs = [30]
n_frames_offset = 0
n_frames_max = -1
n_frames_percent = 100
n_frames_total = 100000
vds_names = ["xmpl_30_vds.cxi"]
cxi_names = ["p2304_r0108.cxi"]
list_prefix = "xmpl_30"

[crystfel]
# Available versions: '0.8.0', '0.9.1', '0.10.1', 'cfel_dev'
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
# Available partitions: 'all', 'upex', 'exfel'
partition = "all"
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
peak_max_px = 2
peaks_hdf5_path = "entry_1/result_1"
index_method = "mosflm"
n_cores = -1
local_bg_radius = 3
max_res = 1200
min_peaks = 0
extra_options = "--no-non-hits-in-stream"

[unit_cell]
file = "/gpfs/exfel/exp/XMPL/201750/p700000/proc/r0030/hewl.cell"
run_refine = false

[frame_filter]
match_tolerance = 0.1

[proc_fine]
resolution = 2.0
integration_radii = "2,3,5"

[partialator_split]
execute = false
# Available modes: "on_off", "on_off_numbered", "by_pulse_id"
mode = "on_off"
# Required only for "on_off" or "on_off_numbered" modes:
xray_signal = ["SPB_LAS_SYS/ADC/UTC1-1:channel_0.output", "data.rawData"]
laser_signal = ["SPB_LAS_SYS/ADC/UTC1-1:channel_1.output", "data.rawData"]
plot_train = 0
# Required only for "by_pulse_id" mode:
[partialator_split.pulse_datasets]
  my_1 = [0,4]
  my_2 = [12, 20]
  my_3 = [24, 48]

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
if [[ $N_CORES_USE -lt 0 ]]
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
%(COPY_FIELDS)s  %(EXTRA_OPTIONS)s

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
if [[ $N_CORES_USE -lt 0 ]]
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
%(COPY_FIELDS)s  %(EXTRA_OPTIONS)s

echo "LOG: finished on $(date +'%%m/%%d/%%Y') at $(date +'%%H:%%M:%%S')."
"""

PARTIALATOR_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh

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
source /usr/share/Modules/init/sh

%(IMPORT_CRYSTFEL)s

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

%(IMPORT_CRYSTFEL)s

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

%(IMPORT_CRYSTFEL)s

cell_explorer %(PREFIX)s.stream
"""

HDFSEE_WRAP = """\
#!/bin/sh
source /usr/share/Modules/init/sh

%(IMPORT_CRYSTFEL)s

hdfsee %(DATA_FILE)s -g %(GEOM)s
"""
