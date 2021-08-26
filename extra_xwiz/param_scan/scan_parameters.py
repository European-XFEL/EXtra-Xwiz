import argparse
import logging
import os.path as osp

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

    log.info("Starting EXtra-xwiz parameters scanner.")

    scan_config = "xwiz_scan_conf.toml"
    if not osp.exists(scan_config):
        with open(scan_config, 'w') as con_f:
            con_f.write(CONFIG_TEMPLATE)
            log.info(f"Scan configuration template written to {scan_config}.")
            exit(0)

    scanner = ParameterScanner(scan_config)

    scanner.make_folders()
    scanner.run_jobs()
    scanner.collect_outputs()

    log.info("EXtra-xwiz parameters scan finished.")

    handler.close()

if __name__ == '__main__':
    main()
