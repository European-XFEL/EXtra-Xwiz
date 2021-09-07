import logging
import os.path as osp
from argparse import ArgumentParser

from .scanner import ParameterScanner
from .template import CONFIG_TEMPLATE

log = logging.getLogger(__name__)


def main(argv=None):
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    # Store logs also to the file
    handler = logging.FileHandler('param_scan.log', 'w')
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s:%(name)s: %(message)s",
        datefmt='%d/%m %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)

    parser = ArgumentParser(
        prog="xwiz-scan-parameters",
        description='Run xwiz scanning through the parameters specified in'
                    'xwiz_scan_conf.toml.'
    )

    parser.add_argument(
        '-xc', '--xwiz_config',
        help="Use specified xwiz configuration file. If this option is"
             " omitted configuration file specified in the scan config"
             " will be used."
    )
    exc_group = parser.add_mutually_exclusive_group()
    exc_group.add_argument(
        '-o', '--output',
        action='store_true',
        help="Skip running xwiz jobs and just collect existing output."
    )
    exc_group.add_argument(
        '-f', '--force',
        action='store_true',
        help="Replace any existing job folders."
    )
    args = parser.parse_args(argv)

    log.info("Starting EXtra-xwiz parameters scanner.")

    scan_config = "xwiz_scan_conf.toml"
    if not osp.exists(scan_config):
        with open(scan_config, 'w') as con_f:
            con_f.write(CONFIG_TEMPLATE)
            log.info(f"Scan configuration template written to {scan_config}.")
            exit(0)

    scanner = ParameterScanner(scan_config, args.xwiz_config, args.force)

    scanner.make_folders()
    if not args.output:
        scanner.run_jobs()
    scanner.collect_outputs()

    log.info("EXtra-xwiz parameters scan finished.")

    handler.close()


if __name__ == '__main__':
    main()
