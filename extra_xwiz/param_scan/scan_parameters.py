import argparse
import logging

from .scanner import ParameterScanner

log = logging.getLogger(__name__)

def main(argv=None):
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s: %(message)s'
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

    scanner = ParameterScanner("xwiz_scan_conf.toml")

    scanner.make_folders()

    pass

    handler.close()

if __name__ == '__main__':
    main()
