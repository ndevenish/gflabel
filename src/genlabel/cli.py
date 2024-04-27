#!/usr/bin/env python3
# ruff: noqa: F403

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from itertools import islice

import build123d as bd

# from build123d import *
from build123d import (
    BuildPart,
    FontStyle,
    Location,
    Locations,
    Mode,
    add,
    export_step,
    extrude,
)

from .bases import plain, pred
from .label import render_divided_label
from .options import LabelStyle, RenderOptions

logger = logging.getLogger(__name__)

if "--vscode" in sys.argv:
    from ocp_vscode import Camera, set_defaults, show

    set_defaults(reset_camera=Camera.CENTER)

# common_args = ArgumentParser(add_help=False)


# Taken from Python 3.12 documentation.
def batched(iterable, n):
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def run(argv: list[str] | None = None):
    parser = ArgumentParser(description="Generate pred-style gridfinity bin labels")
    parser.add_argument(
        "--base",
        choices=["pred", "plain"],
        default="pred",
        help="Label base to generate onto. [Default: %(default)s]",
    )
    parser.add_argument(
        "--vscode",
        help="Run in vscode_ocp mode, and show the label afterwards.",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--width",
        help="Label width, in gridfinity units. Default: %(default)s",
        metavar="WIDTH_U",
        default="1",
    )
    parser.add_argument(
        "labels", nargs="*" if "--vscode" in sys.argv else "+", metavar="LABEL"
    )
    parser.add_argument(
        "-d",
        "--divisions",
        help="How many areas to divide a single label into. If more labels that this are requested, multiple labels will be generated. Default: %(default)s.",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--font",
        help="The font to use for rendering. [Default: %(default)s]",
        type=str,
        default="Futura",
    )
    parser.add_argument(
        "--font-size",
        help="The font size (in mm) to use for rendering. If unset, then the font will use as much vertical space as needed (that also fits within the horizontal area).",
        type=float,
    )
    parser.add_argument(
        "--font-style",
        help="The font style use for rendering. [Default: %(default)s]",
        choices=[x.name.lower() for x in FontStyle],
        default="regular",
        type=str,
    )
    parser.add_argument(
        "--margin",
        help="The margin area (in mm) to leave around the label contents. [Default: %(default)s]",
        default=0.2,
        type=float,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename. [Default: %(default)s]",
        default="label.step",
    )
    parser.add_argument(
        "--style",
        help="How the label contents are formed.",
        choices=LabelStyle,
        default=LabelStyle.EMBOSSED,
        type=LabelStyle,
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG,
    )
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("build123d").setLevel(logging.WARNING)

    # If running in VSCode mode, then we can hardcode a label here
    if not args.labels:
        args.labels = ["{webbolt(pozi)}{...}M3×20"]

    args.width = int(args.width.rstrip("u"))
    args.divisions = args.divisions or len(args.labels)
    args.labels = [x.replace("\\n", "\n") for x in args.labels]

    options = RenderOptions.from_args(args)
    print(options)
    with BuildPart() as part:
        y = 0
        for labels in batched(args.labels, args.divisions):
            with Locations([Location([0, y])]):
                if args.base == "pred":
                    body = pred.body(
                        args.width, recessed=args.style == LabelStyle.EMBOSSED
                    )
                else:
                    body = plain.body(args.width, 12)
                y -= body.part.bounding_box().size.Y + 2
                add(body.part)

                add(
                    render_divided_label(
                        labels, body.area, divisions=args.divisions, options=options
                    )
                )
                extrude(
                    amount=0.4,
                    mode=(
                        Mode.ADD if args.style == LabelStyle.EMBOSSED else Mode.SUBTRACT
                    ),
                )
                # y -= 14
                # part.part.bounding_box().size.Y

    if args.output.endswith(".stl"):
        bd.export_stl(part.part, args.output)
    elif args.output.endswith(".step"):
        export_step(part.part, args.output)
    else:
        print(f"Error: Do not understand output format '{args.output}'")

    if args.vscode:
        bd.export_stl(part.part, "label.stl")
        export_step(part.part, "label.step")
        show(part)


# _FRAGMENTS = {
#     "hexhead": _fragment_hexhead,
#     "bolt": _fragment_bolt,
#     "washer": _fragment_washer,
#     "hexnut": _fragment_hexnut,
#     "nut": _fragment_hexnut,
#     "variable_resistor": _fragment_variable_resistor,
# }

if __name__ == "__main__":
    divisions = 0
    filename = "label.step"

    labels = [
        "{hexnut} M6 {hexnut}",
        "{washer} M3",
        "{hexhead} {bolt(12)}\nM3×12",
        "{variable_resistor}",
        "{hexhead} {bolt(30)}\nM4×30",
    ]
    # divisions = divisions or len(labels)

    run([str(x) for x in [1, *labels, "--divisions", "1"]])
