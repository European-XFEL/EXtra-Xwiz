from argparse import ArgumentParser
from extra_xwiz.utilities import (get_crystal_frames, fit_unit_cell,
                                  replace_cell) 


def check_cells(stream_file, cell_file, out_cell=False):
    print(f'Checking {stream_file} against {cell_file}')
    hit_list, cell_ensemble = get_crystal_frames(stream_file, cell_file)
    with open('xtal_checker_hits.lst', 'w') as f:
        for hit_event in hit_list:
            f.write(f'vds.cxi {hit_event}\n')
    refined_cell = fit_unit_cell(cell_ensemble)
    if out_cell:
        replace_cell(cell_file, refined_cell)


def main(argv=None):
    ap = ArgumentParser(prog="xwiz-cell-checker")
    ap.add_argument('stream_file', help='stream file to parse')
    ap.add_argument('cell_file', help='reference cell file for filtering')
    ap.add_argument('-o', '--out_cell', help='optional cell file to write',
                    action='store_true')
    args = ap.parse_args(argv)
    check_cells(args.stream_file, args.cell_file, out_cell=args.out_cell)
