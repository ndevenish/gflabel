#!/usr/bin/env python3
# ruff: noqa: F403

from __future__ import annotations

import argparse
import logging
import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any, Sequence

import build123d as bd
import pint
import rich
import rich.table

# from build123d import *
from build123d import (
    BuildPart,
    BuildSketch,
    ColorIndex,
    Compound,
    ExportSVG,
    FontStyle,
    Keep,
    Location,
    Locations,
    Mode,
    Plane,
    RectangleRounded,
    Vector,
    add,
    export_step,
    extrude,
)

from . import fragments
from .bases import LabelBase
from .bases.cullenect import CullenectBase
from .bases.modern import ModernBase
from .bases.none import NoneBase
from .bases.plain import PlainBase
from .bases.pred import PredBase, PredBoxBase
from .label import render_divided_label
from .options import LabelStyle, RenderOptions
from .util import IndentingRichHandler, batched, unit_registry

logger = logging.getLogger(__name__)

if "--vscode" in sys.argv:
    from ocp_vscode import Camera, set_defaults, show

    set_defaults(reset_camera=Camera.KEEP)


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


class BaseChoiceAction(argparse.Action):
    """ArgumentParser Action to allow choice field with deprecated (hidden) options"""

    def __call__(self, parser, namespace, values, _option_string=None):
        values = values.lower()
        # Allow using these still
        deprecated_choices = {"webb": "cullenect"}
        if values in deprecated_choices:
            values = deprecated_choices[values]

        choices = ["pred", "plain", "none", "cullenect", "predbox", "modern"]

        if values not in choices:
            # Allow prefix-only of choice name, as long as unambiguous
            partially_chosen = [x for x in choices if x.startswith(values)]
            if len(partially_chosen) == 1:
                # Let's use this!
                values = partially_chosen[0]
            elif len(partially_chosen) > 1:
                sys.exit(
                    f"{parser.prog}: Error: {self.metavar}: Unambiguous partial choice (could be {', '.join(partially_chosen)})"
                )
            else:
                sys.exit(
                    f"{parser.prog}: Error: {self.metavar}: Must be passed explicitly now, and be one of: {', '.join(choices)}"
                )

        setattr(namespace, self.dest, values.lower())

    def format_usage(self):
        print("format_usage")
        return self.option_strings[0]


def base_name_to_subclass(name: str) -> type[LabelBase]:
    """Get the LabelBase subclass instance from the name"""
    bases = {
        "cullenect": CullenectBase,
        "modern": ModernBase,
        "pred": PredBase,
        "predbox": PredBoxBase,
        "plain": PlainBase,
        "none": NoneBase,
        None: NoneBase,
    }
    if name not in bases:
        raise ValueError(
            f"Error: Could not find class instance for base named '{name}'"
        )
    return bases[name]


def run(argv: list[str] | None = None):
    # Handle the old way of specifying base
    if any(x.startswith("--base") for x in (argv or sys.argv)):
        sys.exit(
            "Error: --base is no longer the way to specify base geometry. Please pass in as a direct argument (gflabel <BASE>)"
        )

    parser = ArgumentParser(description="Generate gridfinity bin labels")
    parser.add_argument(
        "base",
        metavar="BASE",
        help="Label base to generate onto (pred, plain, none, cullenect, predbox, modern).",
        action=BaseChoiceAction,
    )
    parser.add_argument(
        "--vscode",
        help="Run in vscode_ocp mode, and show the label afterwards.",
        action="store_true",
    )
    parser.add_argument(
        "-w",
        "--width",
        help="Label width. If using a gridfinity standard base, then this is width in U. Otherwise, width in mm. Specify units e.g. '3mm' to override the default behaviour.",
        metavar="WIDTH",
        type=pint.Quantity,
    )
    parser.add_argument(
        "--height",
        help="Label height, by default in mm. For bases with standard heights, this will overwrite the height, diverging from the standard.",
        metavar="HEIGHT",
        default=None,
        type=pint.Quantity,
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

    parser.add_argument("labels", nargs="+", metavar="LABEL")
    parser.add_argument(
        "-d",
        "--divisions",
        help="How many areas to divide a single label into. If more labels that this are requested, multiple labels will be generated. Default: %(default)s.",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--font",
        help="The name of the system font to use for rendering. If unspecified, a bundled version of Open Sans will be used. Set GFLABEL_FONT in your environment to change the default.",
        type=str,
        default=os.getenv("GFLABEL_FONT"),
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
        "--font-path",
        help="Path to font file, if not using a system-level font.",
        type=Path,
        # default=None,
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
        default=[],
        action="append",
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
        "--label-gap",
        help="Vertical gap (in mm) between physical labels. Default: %(default)s mm",
        default=2,
        type=float,
    )
    parser.add_argument(
        "--column-gap", help="Gap (in mm) between columns", default=0.4, type=float
    )
    parser.add_argument("--box", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("-v", "--verbose", help="Verbose output", action="store_true")
    parser.add_argument(
        "--version",
        help="The version of geometry to use for a given label system (if a system has versions). [Default: latest]",
        default="latest",
    )
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

    base_type = base_name_to_subclass(args.base)

    if not args.output and not args.vscode:
        args.output = ["label.step"]

    # We don't need to generate 3D shapes if we are only doing SVG
    is_2d = args.output and all([x.endswith(".svg") for x in args.output])

    # If running in VSCode mode, then we can hardcode a label here
    if not args.labels:
        args.labels = ["{cullbolt(pozi)}{...}M3×20"]

    # We want to set the width default before validation, so we can check it
    if not args.width:
        if base_type.DEFAULT_WIDTH:
            args.width = base_type.DEFAULT_WIDTH
        else:
            sys.exit(f"Error: Must specify width for label base '{args.base}'.")

    assert isinstance(args.width, pint.Quantity)

    # If we got a dimensionless width, replace with the base default unit
    if args.width.units == unit_registry.dimensionless:
        args.width = pint.Quantity(args.width.magnitude, base_type.DEFAULT_WIDTH_UNIT)
    # Height with unspecified units is mm
    if args.height and args.height.units == unit_registry.dimensionless:
        args.height = pint.Quantity(args.height.magnitude, unit_registry.mm)

    if args.margin is None:
        args.margin = base_type.DEFAULT_MARGIN
    elif args.margin is not pint.Quantity:
        args.margin = pint.Quantity(args.margin, unit_registry.mm)

    logger.info(f"Rendering label with width: {args.width}")

    args.divisions = args.divisions or len(args.labels)
    args.labels = [x.replace("\\n", "\n") for x in args.labels]

    options = RenderOptions.from_args(args)
    logger.debug("Got render options: %s", options)
    body: LabelBase | None = None
    with BuildPart() as part:
        y = 0
        body = base_type(args)

        if body.part:
            y_offset_each_label = body.part.bounding_box().size.Y + args.label_gap
            label_area = body.area
        else:
            # Only occurs if label type has no body e.g. "None"
            if args.height is None:
                args.height = pint.Quantity("12mm")
            y_offset_each_label = args.height.to("mm").magnitude + args.label_gap

            label_area = Vector(
                X=args.width.to("mm").magnitude, Y=args.height.to("mm").magnitude
            )

        body_locations = []
        with BuildSketch(mode=Mode.PRIVATE) as label_sketch:
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

        if args.box and is_2d:
            logger.debug("Generating label outline for --box")
            with BuildSketch(mode=Mode.PRIVATE) as body_box:
                with Locations(body_locations):
                    add(RectangleRounded(label_area.X, label_area.Y, label_area.Y / 10))

        if not is_2d:
            # Create all of the bases
            if body.part:
                logger.debug("Creating label bodies")
                with Locations(body_locations):
                    add(body.part)

            logger.debug("Extruding labels")
            is_embossed = args.style == LabelStyle.EMBOSSED
            extrude(
                label_sketch.sketch,
                amount=args.depth if is_embossed else -args.depth,
                mode=(Mode.ADD if is_embossed else Mode.SUBTRACT),
            )

    if not is_2d:
        part.part.label = "Base"

    if args.style == LabelStyle.EMBEDDED:
        # We want to make new volumes for the label, making it flush
        embedded_label = extrude(label_sketch.sketch, amount=-args.depth)
        embedded_label.label = "Label"
        assembly = Compound([part.part, embedded_label])
    else:
        assembly = Compound(part.part)

    for output in args.output:
        if output.endswith(".stl"):
            logger.info(f"Writing STL {output}")
            bd.export_stl(assembly, output)
        elif output.endswith(".step"):
            logger.info(f"Writing STEP {output}")
            export_step(assembly, output)
        elif output.endswith(".svg"):
            max_dimension = max(
                *label_sketch.sketch.bounding_box().size, label_area.X, label_area.Y
            )
            exporter = ExportSVG(scale=100 / max_dimension)
            exporter.add_layer("Shapes", fill_color=ColorIndex.BLACK, line_weight=0)

            if args.box and is_2d:
                exporter.add_layer("Box", line_weight=1)
                exporter.add_shape(body_box.sketch, layer="Box")
            logger.info(f"Writing SVG {output}")
            exporter.add_shape(label_sketch.sketch, layer="Shapes")
            exporter.write(output)
        else:
            logger.error(f"Error: Do not understand output format '{args.output}'")

    if args.vscode:
        show_parts = []
        show_cols: list[str | tuple[float, float, float] | None] = []
        # Export both step and stl in vscode_ocp mode
        if is_2d:
            show_parts.append(label_sketch.sketch)
        else:
            logger.info("Writing SVG label.stl")
            bd.export_stl(assembly, "label.stl")
            logger.info("Writing STEP label.step")
            export_step(assembly, "label.step")
            if args.style == LabelStyle.EMBEDDED:
                show_parts.append(part.part)
                show_cols.append(None)
                show_parts.append(embedded_label)
                show_cols.append((0.2, 0.2, 0.2))
            else:
                # Split the base for display as two colours
                top = part.part.split(
                    Plane.XY if is_embossed else Plane.XY.offset(-args.depth),
                    keep=Keep.TOP,
                )
                if top:
                    show_parts.append(top)
                    show_cols.append((0.2, 0.2, 0.2))
                if args.base != "none":
                    bottom = part.part.split(Plane.XY, keep=Keep.BOTTOM)
                    if bottom.wrapped:
                        show_parts.append(bottom)
                        show_cols.append(None)

        show(
            *show_parts,
            colors=show_cols,
            # position=[0, -10, 10],
            # target=[0, 0, 0],
        )


if __name__ == "__main__":
    run()
