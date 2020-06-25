import os
import re


def create_new_summary(prefix, geom):
    with open(f'{prefix}.summary', 'w') as f:
        f.write('SUMMARY OF XWIZ WORKFLOW\n\n')
        f.write(f'Geometry file used: {geom}\n\n')
        f.write('Step #   d_lim   source      N(crystals)    N(frames)    Indexing rate [%%]\n')


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


def report_merging_metrics(prefix):
    """Report overall (un-binned) crystallographic figures-of-merit
    """
    labels = ['Completeness', 'Signal-over-noise', 'CC_1/2', 'CC*', 'R_split']
    fstring = ['{:15.2f}', '{:15.2f}', '{:15.4f}', '{:15.4f}', '{:15.2f}']
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\nCrystallographic FOMs:')
        f.write('\n                          overall    outer shell\n')
        for i, table in enumerate(['completeness', 'completeness', 'cchalf',
                                   'ccstar', 'rsplit']):
            cw = [1, 1, 2, 2, 2][i]  # column index for n_reflections = weight
            cf = [3, 6, 1, 1, 1][i]  # column index for respective FOM value
            with open(f'{prefix}_{table}.dat', 'r') as fd:
                data_lines = fd.readlines()[1:]
            w_sum = 0.0
            f_sum = 0.0
            for ln in data_lines:
                item = ln.split()
                w_sum += int(item[cw])
                f_sum += (int(item[cw]) * float(item[cf]))
            # last line = high-resolution shell
            fom_high = float(data_lines[-1].split()[cf])
            f.write('{:18}'.format(labels[i]) + fstring[i].format(f_sum/w_sum)
                    + fstring[i].format(fom_high) + '\n')


def report_reprocess(prefix):
    """Report start of a reprocessing step
    """
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\n###   Reprocessing   ####\n')


def report_config_echo(prefix, conf):
    """Report the initial workflow configuration"""
    with open(f'{prefix}.summary', 'a') as f:
        f.write('\nBASE CONFIGURATION USED\n')
        for group_key, group_dict in conf:
            f.write(f' Group: {group_key}')
            for param_key, param_value in group_dict:
                f.write(f'{param_key:12} {param_value}')


def report_reconfig(prefix, param_key, param_value):
    pass