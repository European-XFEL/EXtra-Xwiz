"""
Module to convert mask from Cheetah or VDS HD5 file to the
geometry file.
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
    the HD5 to geometry file.

    Args:
        argv (string, optional): arguments string. Defaults to None.
    """

    parser = ArgumentParser(
        prog="xwiz-mask-hd52geom",
        description="Read mask from the HD5 file and convert it to "
                    "the geometry file."
    )

    parser.add_argument(
        "input_hd5",
        help="Input HD5 file to read the mask from."
    )
    parser.add_argument(
        "output_geo",
        help="Geometry file to which the converted mask will be written."
    )

    write_mode_group = parser.add_mutually_exclusive_group()
    write_mode_group.add_argument(
        "-r", "--replace",
        action='store_const',
        const='replace',
        default='replace',
        dest='write_mode',
        help="Comment out existing mask before including converted mask, "
             "default behavior."
    )
    write_mode_group.add_argument(
        "-a", "--add",
        action='store_const',
        const='add',
        dest='write_mode',
        help="Add converted mask to the mask which is already in "
             "the geometry file."
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
        help="Invert the mask read from the HD5 file before converting."
    )

    args = parser.parse_args(argv)

    converter = mc.MaskConverter(
        args.input_hd5,
        args.output_geo,
        'hd52geom',
        args.write_mode,
        args.path_hd5,
        args.entry_hd5,
        args.detector,
        args.type,
        args.invert
    )
    converter.convert()
