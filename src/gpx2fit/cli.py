import argparse
import sys
from pathlib import Path

from gpx2fit.converter import SPORT_NAMES, convert_gpx_to_fit, split_gpx_to_fit


def main():
    parser = argparse.ArgumentParser(
        prog="gpx2fit",
        description="Convert GPX files to Garmin FIT format",
    )
    subparsers = parser.add_subparsers(dest="command")

    # convert (default single-file mode)
    convert_parser = subparsers.add_parser(
        "convert", help="Convert a single GPX file to FIT"
    )
    convert_parser.add_argument("gpx_file", type=Path, help="Path to GPX file")
    convert_parser.add_argument(
        "-s",
        "--sport",
        required=True,
        choices=SPORT_NAMES,
        metavar="SPORT",
        help="Sport type for the activity (e.g. running, cycling, hiking, surfing, ...)",
    )
    convert_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output FIT file path (default: input filename with .fit extension)",
    )

    # split (multi-track GPX -> individual FIT files)
    split_parser = subparsers.add_parser(
        "split",
        help="Split a multi-track GPX file into individual FIT files",
    )
    split_parser.add_argument("gpx_file", type=Path, help="Path to GPX file")
    split_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: 'output' in current directory)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if not args.gpx_file.exists():
        print(f"Error: {args.gpx_file} not found", file=sys.stderr)
        sys.exit(1)

    if args.command == "convert":
        output = args.output or args.gpx_file.with_suffix(".fit")
        convert_gpx_to_fit(args.gpx_file, output, args.sport)
        print(f"Converted {args.gpx_file} -> {output}")

    elif args.command == "split":
        output_dir = args.output_dir or Path("output")
        converted, skipped = split_gpx_to_fit(args.gpx_file, output_dir)
        print(f"Converted {converted} activities to {output_dir}/")
        if skipped:
            print(f"Skipped {skipped} tracks (no sport type detected)")
