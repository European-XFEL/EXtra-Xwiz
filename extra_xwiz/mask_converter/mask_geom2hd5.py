"""
Module to convert mask from the geometry to HD5 file.
"""

# Standard library imports
from argparse import ArgumentParser
import warnings

# Local imports
from . import detector_info as di
from . import mask_converter as mc


def main(argv=None):
    """
    Function to be called by the egg entrypoint to convert mask from
    the geometry to HD5 file.

    Args:
        argv (string, optional): arguments string. Defaults to None.
    """

    parser = ArgumentParser(
        prog="xwiz-mask-geom2hd5",
        description="Read mask from the geometry file and convert it "
                    "to the HDF5."
    )

    parser.add_argument(
        "input_geo",
        help="Input geometry file to read the mask from."
    )
    parser.add_argument(
        "output_hd5",
        help="Output HD5 file to which the converted mask will be written."
    )

    write_mode_group = parser.add_mutually_exclusive_group()
    write_mode_group.add_argument(
        "-r", "--replace",
        action='store_const',
        const='replace',
        default='replace',
        dest='write_mode',
        help="Overwrite existing mask in HD5 file (if any) with "
             "converted mask, default behavior."
    )
    write_mode_group.add_argument(
        "-a", "--add",
        action='store_const',
        const='add',
        dest='write_mode',
        help="Add converted mask to the mask in HD5 file (if any)."
    )

    parser.add_argument(
        "-d", "--detector",
        choices=di.detector_info.keys(),
        required=True,
        help="Detector used in the experiment."
    )
    parser.add_argument(
        "-t", "--type",
        choices=di.get_data_types(),
        required=True,
        help="Type of the data stored in HD5 file."
    )

    parser.add_argument(
        "-p", "--path-hd5",
        default='/entry_1/data_1/mask',
        help="Path to the mask data in the HD5 file."
    )
    parser.add_argument(
        "-e", "--entry-hd5",
        type=int,
        default=0,
        help="Number of the mask data entry."
    )
    parser.add_argument(
        "-i", "--invert",
        action='store_true',
        help="Invert the mask before writing to the HD5 file."
    )

    args = parser.parse_args(argv)

    converter = mc.MaskConverter(
        args.output_hd5,
        args.input_geo,
        'geom2hd5',
        args.write_mode,
        args.path_hd5,
        args.entry_hd5,
        args.detector,
        args.type,
        args.invert
    )
    converter.convert()
