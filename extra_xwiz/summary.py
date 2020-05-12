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
