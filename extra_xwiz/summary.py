import os
import re


def create_new_summary(prefix):
    with open(f'{prefix}.summary', 'w') as f:
        f.write('SUMMARY OF XWIZ WORKFLOW\n\n')
        f.write('Step #     source    N(crystals)    N(frames)    Indexing rate [%%]\n')


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
        f.write(' {:2d}  {:3.1f}   indexamajig   {:7d}   {:7d}       {:5.2f}\n'.format(step,
                res_limit, len(cryst_occur), len(frame_occur), indexing_rate))


def report_cell_check(prefix, n_crystals, n_frames):
    """Report indexing success rate wrt. reasonable unit cell
      (status before final processing step).
    """
    indexing_rate = 100.0 * n_crystals / n_frames
    with open(f'{prefix}.summary', 'a') as f:
        f.write('           cell_check    {:7d}   {:7d}       {:5.2f}\n'.format(n_crystals,
                n_frames, indexing_rate))



