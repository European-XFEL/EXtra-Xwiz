"""Prepare a list file for CrystFEL partialator to split frames into
datasets depending on the laser state."""

import json
import os
import h5py
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import multiprocessing as mproc
import numpy as np
import warnings
import xarray as xr

from extra_data import open_run


ALL_DATASET = "all_data"


def plot_adc_signal(
    xray_signal: np.ndarray, laser_signal: np.ndarray, threshold: float,
    pulse_ids: np.ndarray, laser_align: int, laser_per_pulse: np.ndarray
) -> Figure:
    """Prepare a figure with X-ray pulses and laser state signal.

    Parameters
    ----------
    xray_signal : np.ndarray
        Array with X-ray pulses fastADC signal.
    laser_signal : np.ndarray
        Array with PP laser pattern fastADC signal.
    threshold : float
        Threshold (in arbitrary intensity units) to separate diode
        signal from the background.
    pulse_ids : np.ndarray
        Array of pulse peaks positions in the fastADC data.
    laser_align : int
        Shift between PP laser and X-ray pulses signals.
    laser_per_pulse : np.ndarray
        Boolean array with laser state per pulse peak.

    Returns
    -------
    Figure
        Figure with fastADC data used to extract pumping laser state.
    """
    n_samples = xray_signal.shape[0]
    x = np.linspace(0, n_samples, n_samples, endpoint=False)

    fig, axes = plt.subplots(2, 1, figsize=(100, 4))
    fig.tight_layout()

    min_y = max_y = 0
    for dataset in [xray_signal, laser_signal]:
        min_y = np.min(dataset) if np.min(dataset) < min_y else min_y
        max_y = np.max(dataset) if np.max(dataset) > max_y else max_y
    offset_y = 0.1*max_y + 0.9*min_y
    
    for ax, dataset, label, color in zip(
        axes, [xray_signal, laser_signal], ["pulses", "laser"],
        ['royalblue', 'darkorange']
    ):
        ax.plot(x, dataset, color=color)
        ax.plot(
            [0, n_samples], [threshold, threshold], color='lightcoral',
            linestyle='-.'
        )

        ax.set_xlim(0, n_samples)
        ax.set_ylim(min_y-offset_y, max_y+offset_y)
        ax.set_title(label)
        ax.set_ylabel('Intensity')

    axes[0].plot(
        pulse_ids, xray_signal[pulse_ids], color='limegreen', marker="o",
        markersize=4, linestyle='None'
    )
    true_ids = pulse_ids[np.where(laser_per_pulse)[0]] + laser_align
    false_ids = (pulse_ids[np.where(np.logical_not(laser_per_pulse))[0]]
                 + laser_align)
    axes[1].plot(
        true_ids, laser_signal[true_ids], color='limegreen', marker="o",
        markersize=4, linestyle='None'
    )
    axes[1].plot(
        false_ids, laser_signal[false_ids], color='firebrick', marker="o",
        markersize=4, linestyle='None'
    )
    axes[1].set_xlabel('ADC sample #')

    return fig


def get_adc_threshold(signal: np.ndarray) -> float:
    """Estimate threshold in arbitrary intensity units to separate diode
    signal from the background. Set to 5% of the difference between
    signal minimum and maximum values."""
    th_percent = 0.05
    return np.max(signal)*th_percent + np.min(signal)*(1-th_percent)


def align_adc_signal(signal: np.ndarray, peak_ids: np.ndarray) -> int:
    """Align fastADC signal series to have maximum at the expected
    positions of the peak.

    Parameters
    ----------
    signal : np.ndarray
        Array of fastADC signal.
    peak_ids : np.ndarray
        Positions of the expected signal peaks (e.g. positions of the
        pulse signal peaks).

    Returns
    -------
    int
        Alignment parameter - a value by which the signal series have
        to be shifted.
    """
    max_align = np.min(np.ediff1d(peak_ids)) // 4
    align_vals = list(range(-max_align, max_align))
    align_peaks = np.zeros((len(align_vals)))
    for i_align, align_val in enumerate(align_vals):
        align_peaks[i_align] = np.max(signal[peak_ids + align_val])
    return align_vals[np.argmax(align_peaks)]


def get_laser_state_from_diode(
    proposal: int, run: int, xray_signal_src: list, laser_signal_src: list,
    pulse_ids: np.ndarray, folder: str=".", plot_signal: bool=False
) -> xr.DataArray:
    """Estimate PP laser state from the fastADC diode signal.

    Parameters
    ----------
    proposal : int
        Experiment proposal number.
    run : int
        Data collection run number.
    xray_signal_src : list
        Source of the X-ray pulse pattern signal. Should be a list with
        2 strings, source and key, for example:
        ["SPB_LAS_SYS/ADC/UTC1-1:channel_0.output", "data.rawData"]
    laser_signal_src : list
        Source of the PP laser signal. Should be a list in the same
        format as 'xray_signal_src'.
    pulse_ids : np.ndarray
        Array of the pulse id values in the stored detector data.
    folder : str, optional
        Folder to store plots of fastADC data (if any).
    plot_signal : bool, optional
        Whether to plot fastADC data for all unique laser patterns.

    Returns
    -------
    xr.DataArray
        DataArray of the PP laser state for all trains and pulses.
    """
    data_run = open_run(proposal=proposal, run=run, data="all")
    first_tid = int(data_run.train_ids[0])

    n_pulses = pulse_ids.shape[0]
    # laser_per_pulse values: 0 -> 'off', 1 -> 'on', 2 -> 'unknown'
    # By default 2 ('unknown')
    laser_per_pulse_arr = np.full((len(data_run.train_ids), n_pulses), 2)
    # Dictionary with unique laser state patterns (in tuples) as keys
    # and firs trains they appear in as values
    laser_patterns = {}

    data_select = data_run.select(
        [xray_signal_src, laser_signal_src]).trains(require_all=True)
    for train_id, data in data_select:
        xray_signal = np.array(data[xray_signal_src[0]][xray_signal_src[1]])
        laser_signal = np.array(data[laser_signal_src[0]][laser_signal_src[1]])

        threshold = get_adc_threshold(xray_signal)
        pulses_thr = np.array(xray_signal) > threshold
        laser_thr = np.array(laser_signal) > threshold

        pulse_pos = np.where(np.roll(pulses_thr,1)<pulses_thr)[0]
        align_val = align_adc_signal(laser_signal, pulse_pos)
        laser_per_pulse = laser_thr[pulse_pos + align_val].astype(int)

        # Plot X-ray pulses and PP laser data for unique patterns
        if plot_signal:
            file_base = f"fastADC_p{proposal}_r{run:04d}_tid"
            curr_laser_pattern = tuple(laser_per_pulse)
            if curr_laser_pattern not in laser_patterns:
                laser_patterns[curr_laser_pattern] = train_id
                adc_figure = plot_adc_signal(
                    xray_signal, laser_signal, threshold, pulse_pos,
                    align_val, laser_per_pulse
                )
                adc_figure.savefig(
                    f"{folder}/{file_base}{train_id}.png",
                    dpi=300, bbox_inches="tight"
                )
                with open(f"{folder}/{file_base}{train_id}.txt", "w") as ftxt:
                    ftxt.write(f"Laser pattern:\n")
                    ftxt.write(f"    {curr_laser_pattern}\n")
                    ftxt.write(f"Trains:\n")
                    ftxt.write(f"    {train_id}\n")
            else:
                orig_tid = laser_patterns[curr_laser_pattern]
                with open(f"{folder}/{file_base}{orig_tid}.txt", "a") as ftxt:
                    ftxt.write(f"    {train_id}\n")

        n_pulses_curr = laser_per_pulse.shape[0]
        if n_pulses_curr == n_pulses:
            laser_per_pulse_arr[(train_id-first_tid)] = laser_per_pulse
        else:
            warnings.warn(
                f"Found only {n_pulses_curr} pulses for train {train_id} "
                f"while expected {n_pulses}. Assigning frames to 'unknown'.")

    laser_per_train_pulse = xr.DataArray(
        laser_per_pulse_arr,
        coords=[data_run.train_ids, pulse_ids],
        dims=["trainId", "pulseId"]
    )
    return laser_per_train_pulse


def store_laser_pattern(laser_state: xr.DataArray, folder: str) -> None:
    """Store in the specified folder PP laser state DataArray as
    a netCDF file and, if state is the same for all trains, as a json
    file with a list of laser states per pulse."""
    laser_state.to_netcdf(f"{folder}/laser_per_train_pulse.nc")
    pattern_mismatch = laser_state.data[1:] != laser_state.data[:-1]
    n_mismatch = np.unique(np.where(pattern_mismatch)[0]).shape[0]
    if n_mismatch > 0:
        warnings.warn(
            f"Laser pattern mismatch for {n_mismatch} trains, could not "
            f"convert into a single array.")
    else:
        pattern_lst = [int(val) for val in laser_state[0].data]
        with open(f"{folder}/laser_per_pulse.json", 'w') as j_file:
            json.dump(pattern_lst, j_file)


class DatasetSplitter:

    def __init__(
        self, proposal: int, run: int, vds_file: str, folder: str,
        split_config: dict
    ):
        """Split detector frames into datasets depending on the PP laser
        state.

        Parameters
        ----------
        proposal : int
            Experiment proposal number.
        run : int
            Data collection run number.
        vds_file : str
            VDS file with the detector data.
        folder : str
            Current working folder.
        split_config : dict
            Dictionary with the partialator split parameters.
        """
        self.vds_file = vds_file
        with h5py.File(self.vds_file, 'r') as vds_f:
            self.frame_trains = np.array(vds_f['/entry_1/trainId'])
            self.frame_pulses = np.array(vds_f['/entry_1/pulseId'])
            self.n_frames = self.frame_trains.shape[0]
        self.pulses_array = self.get_pulses_array()

        if not os.path.exists(folder):
            os.makedirs(folder)
        self.folder = folder

        self.mode = split_config['mode']
        if self.mode in ['on_off', 'on_off_numbered']:
            self.laser_state = get_laser_state_from_diode(
                proposal=proposal,
                run=run,
                xray_signal_src=split_config['xray_signal'],
                laser_signal_src=split_config['laser_signal'],
                pulse_ids=self.pulses_array,
                folder=self.folder,
                plot_signal=split_config['plot_signal']
            )
            store_laser_pattern(self.laser_state, self.folder)
        elif self.mode == 'by_pulse_id':
            pulse_datasets = split_config['pulse_datasets']
            if ALL_DATASET in pulse_datasets:
                raise ValueError(
                    f"Dataset name '{ALL_DATASET}' is reserved - please "
                    f"use a different dataset name.")

            self.range_dataset = dict()
            for p_dataset in pulse_datasets:
                if isinstance(pulse_datasets[p_dataset][0], list):
                    for p_rng in pulse_datasets[p_dataset]:
                        self.range_dataset[(p_rng[0], p_rng[1])] = p_dataset
                else:
                    p_rng = pulse_datasets[p_dataset]
                    self.range_dataset[(p_rng[0], p_rng[1])] = p_dataset

        self.all_datasets = set()

    def get_pulses_array(self) -> np.ndarray:
        """Estimate array of the pulse id values from the stored
        detector data."""
        trains_pos = np.append(
            np.where(np.roll(self.frame_trains,1) != self.frame_trains),
            self.frame_trains.shape[0]
        )
        trains_pos_diff = np.ediff1d(trains_pos)
        n_pulses = round(np.median(trains_pos_diff))

        incomplete_trains_pos = trains_pos[np.where(trains_pos_diff != n_pulses)]
        self.incomplete_trains = self.frame_trains[incomplete_trains_pos]
        if self.incomplete_trains.shape[0] != 0:
            warnings.warn(
                f"Expected {n_pulses} pulses in each train, but different "
                f"n_pulses found for train(s) "
                f"{', '.join([str(tid) for tid in self.incomplete_trains])}.")

        for train_pos in trains_pos:
            if train_pos not in incomplete_trains_pos:
                pulses_array = self.frame_pulses[train_pos:train_pos+n_pulses]
                break
        else:
            raise RuntimeError(
                f"Could not retrieve pulse ids pattern from vds file "
                f"{self.vds_file}.")

        return pulses_array

    def decode_state(self, train_id, pulse_id) -> str:
        """Decode laser state from self.laser_state for specified
        train_id and pulse_id."""
        if (train_id not in self.incomplete_trains
            and train_id in self.laser_state.trainId
            and pulse_id in self.laser_state.pulseId):
            curr_state = int(self.laser_state.loc[train_id, pulse_id])
            return ['off', 'on', 'unknown'][curr_state]
        else:
            return 'unknown'

    def find_dataset(self, frame_id: int) -> str:
        """Estimate dataset name for the specified data frame id."""
        train_id = self.frame_trains[frame_id]
        pulse_id = self.frame_pulses[frame_id]

        if self.mode == 'on_off':
            dataset = self.decode_state(train_id, pulse_id)
        elif self.mode == 'on_off_numbered':
            state_base = self.decode_state(train_id, pulse_id)
            if state_base in ['off', 'on']:
                state_array = np.array(self.laser_state.loc[train_id,:pulse_id])
                state_change = np.where(np.roll(state_array,1)!=state_array)[0]
                if state_change.shape[0] > 0:
                    state_num = state_array.shape[0] - state_change[-1]
                else:
                    state_num = state_array.shape[0]
                dataset = f'{state_base}_{state_num}'
            else:
                dataset = state_base
        elif self.mode == 'by_pulse_id':
            for cur_range in self.range_dataset:
                if pulse_id >= cur_range[0] and pulse_id <= cur_range[1]:
                    dataset = self.range_dataset[cur_range]
                    break
            else:
                dataset = 'unknown'

        self.all_datasets.add(dataset)
        return dataset


    def get_frame_line(self, frame_id: int, dataset: str) -> str:
        """Compile a string with VDS file name, specified frame id and
        provided dataset name in the partialator list file format."""
        return f"{self.vds_file} //{frame_id} {dataset}"


    def get_split_list(self) -> list:
        """Compile a list of strings with VDS file name, frame id and
        dataset name in the partialator list file format for all data
        frames."""
        with mproc.Pool() as pool:
            datasets = pool.map(self.find_dataset, range(self.n_frames))
            self.all_datasets = set(datasets)
            frame_datasets = pool.starmap(
                self.get_frame_line, zip(range(self.n_frames), datasets)
            )
            return frame_datasets
