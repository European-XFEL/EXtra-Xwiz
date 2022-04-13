from datetime import datetime
import os
import re
from typing import TextIO, Any
import xarray as xr


def config_to_summary(
    sum_file: TextIO, conf: Any, param_key: str=None, indent: int=0
    ):
    """Write config dictionary to the summary file.

    Parameters
    ----------
    sum_file : TextIO
        Summary file to write to.
    conf : Any
        Config dictionary or parameter.
    param_key : str, optional
        Key to the current config dictionary or parameter.
    indent : int, optional
        Desired indentation for the config block, by default 0
    """
    indent_step = 3
    if isinstance(conf, dict):
        if param_key is not None:
            sum_file.write(f"{'':^{indent}}Group: {param_key}\n")
            indent += indent_step
        for key in conf:
            config_to_summary(sum_file, conf[key], key, indent)
    else:
        sum_file.write(f"{'':^{indent}}{param_key:15}: {conf}\n")


def create_new_summary(prefix, conf, is_interactive, use_cheetah):
    """ Initiate a new summary file including timestamp.
        Report the complete initial workflow configuration
    """
    time_stamp = datetime.now().isoformat()
    mode = ['automatic (batch run from configuration file)',
            'interactive (run-time parameter confirm/override)'][is_interactive]
    input_type = ['virtual data set referring to EuXFEL-corrected HDF5',
                  'HDF5 pre-processed with Cheetah'][use_cheetah]
    with open(f'{prefix}.summary', 'w') as sum_file:
        sum_file.write('SUMMARY OF XWIZ WORKFLOW\n\n')
        sum_file.write(f'Session time-stamp: {time_stamp}\n')
        sum_file.write(f'Operation mode:\n  {mode}\n')
        sum_file.write(f'Input type:\n  {input_type}\n')
        sum_file.write('\nBASE CONFIGURATION USED\n')
        config_to_summary(sum_file, conf, indent=1)
        sum_file.write('\n')


def report_step_rate(prefix, stream_file, step, res_limit, n_frames):
    """Parse assembled indexamajig stream file for frames and crystals.
       Calculate indexing rate and report to summary file.
    """
    if not os.path.exists(stream_file):
        return
    n_cryst = len(
        re.findall('Cell parameters', open(stream_file).read(), re.DOTALL)
    )
    indexing_rate = 100.0 * n_cryst / n_frames
    with open(f'{prefix}.summary', 'a') as f:
        f.write(
            "Step #   d_lim   source      N(crystals)    N(frames)    "
            "Indexing rate [%%]\n"
        )
        f.write(
            f" {step:2d}        {res_limit:3.1f}   indexamajig   "
            f"{n_cryst:7d}     {n_frames:7d}         {indexing_rate:5.2f}\n"
        )


def report_cell_check(prefix, n_crystals, n_frames):
    """Report indexing success rate wrt. reasonable unit cell
      (status before final processing step).
    """
    indexing_rate = 100.0 * n_crystals / n_frames
    with open(f'{prefix}.summary', 'a') as f:
        f.write(
            f"                 cell_check    {n_crystals:7d}     "
            f"{n_frames:7d}         {indexing_rate:5.2f}\n"
        )


def report_total_rate(prefix, n_frames):
    """Report overall hit rate as ratio between crystals in last stream file
       and total number of frames, as per initial setting.
    """
    stream_file = f'{prefix}_hits.stream'
    n_cryst = len(
        re.findall('Cell parameters', open(stream_file).read(), re.DOTALL)
    )
    indexing_rate = 100.0 * n_cryst / n_frames
    with open(f'{prefix}.summary', 'a') as f:
        f.write(
            f"                 OVERALL       {n_cryst:7d}     "
            f"{n_frames:7d}         {indexing_rate:5.2f}\n"
        )


def report_cells(prefix, cell_strings):
    """Report unit cell parameters from all files used during the workflow,
       in sequential order.
    """
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\nCrystal unit cells used:\n\n')
        f.write('File                Symmetry/axis, a, b, c, alpha, beta, gamma\n')
        for string in cell_strings:
            f.write(string)


def report_merging_metrics(
    partialator_foms: xr.DataArray, prefix :str
) -> None:
    """Report overall (un-binned) crystallographic figures-of-merit."""
    datasets = partialator_foms.coords['dataset'].values
    shells = partialator_foms.coords['shell'].values
    foms = partialator_foms.coords['fom'].values
    n_foms = len(foms)
    max_ds_len = 28
    for dataset in datasets:
        max_ds_len = max(max_ds_len, len(dataset))
    sh_len = max_ds_len // len(shells)
    sh_left = max_ds_len - sh_len*len(shells)
    
    foms_text = []
    foms_text.append("\nCrystallographic FOMs:")
    foms_text.append(" "*17)
    foms_text.append(" "*17)
    for fom in foms:
        foms_text.append(f"{fom:17}")
    for dataset in datasets:
        foms_text[1] += dataset.center(max_ds_len)
        for i_row in range(2, 3+n_foms):
            foms_text[i_row] += " "*sh_left
        for shell in shells:
            foms_text[2] += f"{shell:>{sh_len}}"
            for i_fom, fom in enumerate(foms):
                fom_val = partialator_foms.loc[dataset, shell, fom].item()
                foms_text[3+i_fom] += f"{fom_val:{sh_len}.3}"

    with open(f'{prefix}.summary', 'a') as f:
        for line in foms_text:
            f.write(line + "\n")


def report_reprocess(prefix):
    """Report start of a reprocessing step
    """
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\n####   Reprocessing   ####\n')


def report_reconfig(prefix, overrides):
    """List all instances where the config-file parameters were
    overridden."""
    if len(overrides) == 0:
        return
    with open(f'{prefix}.summary', 'a') as sum_file:
        sum_file.write('\nPARAMETERS SET IN THE INTERACTIVE MODE\n')
        config_to_summary(sum_file, overrides, indent=1)
