#!/usr/bin/env python3
# ruff: noqa: F403

from __future__ import annotations

import argparse
import logging
import sys
from argparse import ArgumentParser
from itertools import islice
from typing import Any, Sequence

import build123d as bd
import rich
import rich.table

# from build123d import *
from build123d import (
    BuildPart,
    BuildSketch,
    ColorIndex,
    ExportSVG,
    FontStyle,
    Keep,
    Location,
    Locations,
    Mode,
    Plane,
    Vector,
    add,
    export_step,
    extrude,
)

from . import fragments
from .bases import plain, pred, webb
from .label import render_divided_label
from .options import LabelStyle, RenderOptions
from .util import IndentingRichHandler

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


class ListFragmentsAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        table = rich.table.Table("NAMES", "DESCRIPTION")

        frags = fragments.fragment_description_table()
        multiline = [x for x in frags if len(x.description.splitlines()) > 1]

        for frag in multiline:
            table.add_row(", ".join(frag.names), frag.description, end_section=True)
        for frag in [x for x in frags if x not in multiline]:
            table.add_row(", ".join(frag.names), frag.description)

        rich.print(table)
        sys.exit(0)


class ListSymbolsAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(
        self,
        parser: ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        manifest = fragments.electronic_symbols_manifest()
        cols = ["ID", "Category", "Name", "Standard", "Filename"]
        table = rich.table.Table(*cols)
        for symbol in manifest:
            table.add_row(*[symbol[x.lower()] for x in cols])  # type: ignore
        rich.print(table)
        rich.print(
            "\nSymbol Library © Chris Pikul with MIT License https://github.com/chris-pikul/electronic-symbols"
        )
        sys.exit(0)


def run(argv: list[str] | None = None):
    parser = ArgumentParser(description="Generate gridfinity bin labels")
    parser.add_argument(
        "--base",
        choices=["pred", "plain", "none", "webb"],
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
        help="Label width. If using a gridfinity standard base, then this is width in U. Otherwise, width in mm.",
        metavar="WIDTH",
    )
    parser.add_argument(
        "--height",
        help="Label height, in mm. Ignored for standardised label bases.",
        metavar="HEIGHT",
        default=12,
        type=float,
    )
    parser.add_argument(
        "--depth",
        help="How high (or deep) the label extrusion is.",
        metavar="DEPTH_MM",
        default=0.4,
        type=float,
    )
    parser.add_argument(
        "--no-overheight",
        help="Disable the 'Overheight' system. This allows some symbols to oversize, meaning that the rest of the line will first shrink before they are shrunk.",
        action="store_true",
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

    font_size = parser.add_mutually_exclusive_group()
    font_size.add_argument(
        "--font-size-maximum",
        help="Specify a maximum font size (in mm) to use for rendering. The text may end up smaller than this if it needs to fit in the area.",
        type=float,
    )
    font_size.add_argument(
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
        help="The margin area (in mm) to leave around the label contents. Default is per-base.",
        type=float,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename(s). [Default: %(default)s]",
        default=["label.step"],
        nargs="*",
    )
    parser.add_argument(
        "--style",
        help="How the label contents are formed.",
        choices=LabelStyle,
        default=LabelStyle.EMBOSSED,
        type=LabelStyle,
    )
    parser.add_argument(
        "--list-fragments",
        help="List all available fragments.",
        action=ListFragmentsAction,
    )
    parser.add_argument(
        "--list-symbols",
        help="List all available electronic symbols",
        action=ListSymbolsAction,
    )
    parser.add_argument(
        "--gap",
        help="Vertical gap (in mm) between physical labels. Default: %(default)s mm",
        default=2,
        type=float,
    )
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        handlers=[
            IndentingRichHandler(
                show_time=args.verbose,
                show_level=args.verbose,
                show_path=args.verbose,
                log_time_format="[%Y-%m-%d %H:%M:%S]",
            )
        ],
        format="%(message)s",
    )
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("build123d").setLevel(logging.WARNING)

    logger.debug(f"Args: {args}")

    # We cannot have debossed labels with no label
    assert not (args.base == "none" and args.style == LabelStyle.DEBOSSED)

    # We don't need to generate 3D shapes if we are only doing SVG
    is_2d = all([x.endswith(".svg") for x in args.output])

    # If running in VSCode mode, then we can hardcode a label here
    if not args.labels:
        args.labels = ["{webbolt(pozi)}{...}M3×20"]

    if not args.width:
        if args.base in {"pred", "webb"}:
            args.width = "1"
        else:
            sys.exit(f"Error: Must specify width for label base '{args.base}'.")

    if not args.margin:
        if args.base == "webb":
            args.margin = 0
        else:
            args.margin = 0.2
    args.width = int(args.width.rstrip("u"))
    args.divisions = args.divisions or len(args.labels)
    args.labels = [x.replace("\\n", "\n") for x in args.labels]

    options = RenderOptions.from_args(args)
    logger.debug("Got render options: %s", options)
    with BuildPart() as part:
        y = 0
        if args.base == "pred":
            body = pred.body(args.width, recessed=args.style == LabelStyle.EMBOSSED)
        elif args.base == "plain":
            if args.width < 10:
                logger.warning(
                    f"Warning: Small width ({args.width}) for plain base. Did you specify in mm?"
                )
            body = plain.body(args.width, args.height)
        elif args.base == "webb":
            body = webb.body()
        else:
            body = None

        if body:
            y_offset_each_label = body.part.bounding_box().size.Y + args.gap
            label_area = body.area
        else:
            y_offset_each_label = args.height + args.gap
            label_area = Vector(X=args.width, Y=args.height)

        body_locations = []
        with BuildSketch() as label_sketch:
            all_labels = []
            for labels in batched(args.labels, args.divisions):
                body_locations.append((0, y))
                try:
                    all_labels.append(
                        render_divided_label(
                            labels,
                            label_area,
                            divisions=args.divisions,
                            options=options,
                        ).locate(Location([0, y]))
                    )
                except fragments.InvalidFragmentSpecification as e:
                    rich.print(f"\n[y][b]Could not proceed: {e}[/b][/y]\n")
                    sys.exit(1)
                y -= y_offset_each_label
            logger.debug("Combining all labels")
            add(all_labels)

        if not is_2d:
            # Create all of the bases
            if body:
                logger.debug("Creating label bodies")
                with Locations(body_locations):
                    add(body.part)

            logger.debug("Extruding labels")
            extrude(
                amount=args.depth,
                mode=(Mode.ADD if args.style == LabelStyle.EMBOSSED else Mode.SUBTRACT),
            )

    for output in args.output:
        if output.endswith(".stl"):
            bd.export_stl(part.part, output)
        elif output.endswith(".step"):
            export_step(part.part, output)
        elif output.endswith(".svg"):
            max_dimension = max(label_sketch.sketch.bounding_box().size)
            exporter = ExportSVG(scale=100 / max_dimension)
            exporter.add_layer("Shapes", fill_color=ColorIndex.BLACK, line_weight=0)
            logger.info(f"Writing SVG {output}")
            exporter.add_shape(label_sketch.sketch, layer="Shapes")
            exporter.write(output)
        else:
            logger.error(f"Error: Do not understand output format '{args.output}'")

    if args.vscode:
        # Export both step and stl in vscode_ocp mode
        bd.export_stl(part.part, "label.stl")
        export_step(part.part, "label.step")
        # Split the base for display as two colours
        show_parts = []
        show_cols: list[str | tuple[float, float, float] | None] = []
        top = part.part.split(Plane.XY, keep=Keep.TOP)
        if top:
            show_parts.append(top)
            show_cols.append((0.2, 0.2, 0.2))
        if args.base != "none":
            bottom = part.part.split(Plane.XY, keep=Keep.BOTTOM)
            if bottom:
                show_parts.append(bottom)
                show_cols.append(None)

        show(
            *show_parts,
            colors=show_cols,
            # position=[0, -10, 10],
            # target=[0, 0, 0],
        )
