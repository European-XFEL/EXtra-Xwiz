from datetime import datetime
import os
import re


def create_new_summary(prefix, conf, is_interactive, use_cheetah):
    """ Initiate a new summary file including timestamp.
        Report the complete initial workflow configuration
    """
    time_stamp = datetime.now().isoformat()
    mode = ['automatic (batch run from configuration file)',
            'interactive (run-time parameter confirm/override)'][is_interactive]
    input_type = ['virtual data set referring to EuXFEL-corrected HDF5',
                  'HDF5 pre-processed with Cheetah'][use_cheetah]
    with open(f'{prefix}.summary', 'w') as f:
        f.write('SUMMARY OF XWIZ WORKFLOW\n\n')
        f.write(f'Session time-stamp: {time_stamp}\n')
        f.write(f'Operation mode:\n  {mode}\n')
        f.write(f'Input type:\n  {input_type}\n')
        f.write('\nBASE CONFIGURATION USED\n')
        for group_key, group_dict in conf.items():
            f.write(f' Group: {group_key}\n')
            for param_key, param_value in group_dict.items():
                f.write(f'   {param_key:12}: {param_value}\n')


def report_step_rate(prefix, stream_file, step, res_limit):
    """Parse assembled indexamajig stream file for frames and crystals.
       Calculate indexing rate and report to summary file.
    """
    if not os.path.exists(stream_file):
        return
    frame_occur = re.findall('Event: //', open(stream_file).read(), re.DOTALL)
    cryst_occur = re.findall('Cell parameters', open(stream_file).read(),
                             re.DOTALL)
    indexing_rate = 100.0 * len(cryst_occur) / len(frame_occur)
    with open(f'{prefix}.summary', 'a') as f:
        f.write('Step #   d_lim   source      N(crystals)    N(frames)    Indexing rate [%%]\n')
        f.write(' {:2d}        {:3.1f}   indexamajig   {:7d}     {:7d}         {:5.2f}\n'.format(step,
                res_limit, len(cryst_occur), len(frame_occur), indexing_rate))


def report_cell_check(prefix, n_crystals, n_frames):
    """Report indexing success rate wrt. reasonable unit cell
      (status before final processing step).
    """
    indexing_rate = 100.0 * n_crystals / n_frames
    with open(f'{prefix}.summary', 'a') as f:
        f.write('                 cell_check    {:7d}     {:7d}         {:5.2f}\n'.format(n_crystals,
                n_frames, indexing_rate))


def report_total_rate(prefix, n_total):
    """Report overall hit rate as ratio between crystals in last stream file
       and total number of frames, as per initial setting.
    """
    cryst_occur = re.findall('Cell parameters',
                             open(f'{prefix}_hits.stream').read(), re.DOTALL)
    indexing_rate = 100.0 * len(cryst_occur) / n_total
    with open(f'{prefix}.summary', 'a') as f:
        f.write('                 OVERALL       {:7d}     {:7d}         {:5.2f}\n'.format(len(cryst_occur),
                n_total, indexing_rate))


def report_cells(prefix, cell_strings):
    """Report unit cell parameters from all files used during the workflow,
       in sequential order.
    """
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\nCrystal unit cells used:\n\n')
        f.write('File                Symmetry/axis, a, b, c, alpha, beta, gamma\n')
        for string in cell_strings:
            f.write(string)


def report_merging_metrics(part_dir, prefix, log_items):
    """Report overall (un-binned) crystallographic figures-of-merit
    """
    labels = ['Completeness', 'Signal-over-noise', 'CC_1/2', 'CC*', 'R_split']
    fstring = ['{:15.2f}', '{:15.2f}', '{:15.4f}', '{:15.4f}', '{:15.2f}']
    it_tags = ['', '<snr>', 'CC', 'CC*', 'Rsplit'] # as in the log_items list

    with open(f'{prefix}.summary', 'a') as f:
        f.write('\nCrystallographic FOMs:')
        f.write('\n                          overall    outer shell\n')
        for i, table in enumerate(['completeness', 'completeness', 'cchalf',
                                   'ccstar', 'rsplit']):
            cw = [1, 1, 2, 2, 2][i]  # column index for n_reflections = weight
            cf = [3, 6, 1, 1, 1][i]  # column index for respective FOM value

            with open(f'{part_dir}/{prefix}_{table}.dat', 'r') as fd:
                data_lines = fd.readlines()[1:]
            '''
            overall completeness as weighted average; else taken from captured
            STDERR of check_hkl and compare_hkl tool (list 'log_items')
            '''
            if i == 0:
                w_sum = 0.0
                f_sum = 0.0
                for ln in data_lines:
                    item = ln.split()
                    w_sum += int(item[cw])
                    f_sum += (int(item[cw]) * float(item[cf]))
                fom_all = f_sum / w_sum
            else:
                fom_all = float(log_items[log_items.index(it_tags[i]) + 2])

            # last line = high-resolution shell
            fom_high = float(data_lines[-1].split()[cf])

            f.write('{:18}'.format(labels[i]) + fstring[i].format(fom_all)
                    + fstring[i].format(fom_high) + '\n')


def report_reprocess(prefix):
    """Report start of a reprocessing step
    """
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\n####   Reprocessing   ####\n')


def report_reconfig(prefix, overrides):
    """List all instances where the config-file parameters were overridden
    """
    if len(overrides) == 0:
        return
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\nINTERACTIVE PARAMETER OVERRIDES\n')
        for param_key, param_value in overrides.items():
            f.write(f'   {param_key:18}: {param_value}\n')
