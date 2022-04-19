"""Functions to import CrystFEL project file into Xwiz config."""
from argparse import ArgumentParser
import toml

from . import utilities as utl


def import_crystfel_project(
    xwiz_config: str, crystfel_project: str, output_config: str
) -> None:
    """Import CrystFEL project file and transfer parameters to the Xwiz
    configuration.

    Parameters
    ----------
    xwiz_config : str
        Path to the input Xwiz configuration file.
    crystfel_project : str
        Path to the CrystFEL project file.
    output_config : str
        Output Xwiz configuration.
    """
    xwiz_conf = toml.load(xwiz_config)
    with open(crystfel_project, 'r') as proj_file:
        proj_lines = proj_file.readlines()
        
        int_radii = [-1, -1, -1]
        for line in proj_lines:
            param = line.split()
            if param[0] == 'geom':
                utl.set_dotdict_val(xwiz_conf, 'geom.file_path', param[1])
            elif param[0] == 'peak_search_params.method':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.peak_method', param[1])
            elif param[0] == 'peak_search_params.threshold':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.peak_threshold', float(param[1]))
            elif param[0] == 'peak_search_params.min_snr':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.peak_snr', float(param[1]))
            elif param[0] == 'peak_search_params.min_pix_count':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.peak_min_px', int(param[1]))
            elif param[0] == 'peak_search_params.max_pix_count':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.peak_max_px', int(param[1]))
            elif param[0] == 'peak_search_params.local_bg_radius':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.local_bg_radius', int(param[1]))
            elif param[0] == 'peak_search_params.max_res':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.max_res', int(param[1]))
            elif param[0] == 'indexing.cell_file':
                utl.set_dotdict_val(
                    xwiz_conf, 'unit_cell.file', param[1])
            elif param[0] == 'indexing.methods':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.index_method', param[1])
            elif param[0] == 'indexing.min_peaks':
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.min_peaks', int(param[1]))
            elif param[0] == 'integration.ir_inn':
                int_radii[0] = param[1]
            elif param[0] == 'integration.ir_mid':
                int_radii[1] = param[1]
            elif param[0] == 'integration.ir_out':
                int_radii[2] = param[1]
                str_int_radii = ",".join(int_radii)
                utl.set_dotdict_val(
                    xwiz_conf, 'proc_coarse.integration_radii', str_int_radii)
            elif param[0] == 'merging.model':
                utl.set_dotdict_val(
                    xwiz_conf, 'merging.scaling_model', param[1])
            elif param[0] == 'merging.niter':
                utl.set_dotdict_val(
                    xwiz_conf, 'merging.scaling_iterations', int(param[1]))
            elif param[0] == 'merging.max_adu':
                utl.set_dotdict_val(
                    xwiz_conf, 'merging.max_adu', float(param[1]))
    with open(output_config, 'w') as out_file:
        toml.dump(xwiz_conf, out_file)
    print(f'CrystFEL project file imported into "{output_config}".')


def main(argv=None):
    ap = ArgumentParser(prog="xwiz-import-project")
    ap.add_argument(
        'input_config',
        help='Input Xwiz config file'
    )
    ap.add_argument(
        'project_file',
        help='Input CrystFEL project file'
    )
    ap.add_argument(
        'output_config',
        help='Output Xwiz config file'
    )
    args = ap.parse_args(argv)

    import_crystfel_project(
        args.input_config, args.project_file, args.output_config
    )
