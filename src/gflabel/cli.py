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
    Color,
    Compound,
    ExportSVG,
    FontStyle,
    Keep,
    Location,
    Locations,
    Mode,
    Part,
    Plane,
    RectangleRounded,
    Solid,
    Vector,
    add,
    export_step,
    export_stl,
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


def colored_parts(comp: Compound) -> list(Part):
    """Walk the tree of comp to get a list of individual Part objects. Adjust their local locatons to globals along the way."""
    part_list = []
    for child in comp.children:
        if isinstance(child, Part):
            # we clone the part so that the move() calls don't modify things in place
            clone = Part(child)
            clone.label = child.label
            clone.color = child.color
            clone.move(comp.location)
            part_list.append(clone)
        elif isinstance(child, Compound):
            child_part_list = colored_parts(child)
            for child_part in child_part_list:
                clone_part = Part(child_part)
                clone_part.label = child_part.label
                clone_part.color = child_part.color
                clone_part.move(comp.location)
                part_list.append(clone_part)
    return part_list

def run(argv: list[str] | None = None):
    # Handle the old way of specifying base
    if any((x.startswith("--base") and x != "--base-color") for x in (argv or sys.argv)):
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
        "--label-depth",
        help="Label depth, by default in mm.",
        metavar="DEPTH",
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
        "--base-color",
        help="The name of a color used for rendering the base. Can be any of the recognized CSS3 color names.",
        type=str,
        default="orange",
    )
    parser.add_argument(
        "--label-color",
        help="The name of a color used for rendering the label contents. Can be any of the recognized CSS3 color names. Ignored for style 'debossed'.",
        type=str,
        default="blue",
    )
    parser.add_argument(
        "--svg-mono",
        help="SVG files are normally produced with the same colors as the label contents. If you specify this argument, they are produced with label contents in the default label color.",
        action="store_true",
        default=False,
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

    if args.label_depth and args.label_depth.units == unit_registry.dimensionless:
        args.label_depth = pint.Quantity(args.label_depth.magnitude, unit_registry.mm)

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
    with BuildPart() as base_bpart:
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
        child_pcomps = []
        batch_iter = batched(args.labels, args.divisions)
        for ba in batch_iter:
            labels = ba
            xy = Location([0, y])
            body_locations.append((0, y))
            with Locations([xy]):
                try:
                    ch_pc = render_divided_label(
                            labels,
                            label_area,
                            divisions=args.divisions,
                            options=options,
                        )
                    ch_pc.locate(xy)
                    ch_pc.label = "Label_" + str(len(child_pcomps)+1)
                    child_pcomps.append(ch_pc)

                except fragments.InvalidFragmentSpecification as e:
                    rich.print(f"\n[y][b]Could not proceed: {e}[/b][/y]\n")
                    sys.exit(1)
            y -= y_offset_each_label

        label_compound = Compound(children=child_pcomps)
        label_compound.label = "Label"
        logger.debug(f"LABEL COMPOUND {label_compound}\n{label_compound.show_topology()}")

        if not is_2d:
            # Create all of the bases
            if body.part:
                logger.debug("Creating label bodies")
                with Locations(body_locations):
                    add(body.part)

    if args.box and is_2d:
        logger.debug("Generating label outline for --box")
        with BuildSketch(mode=Mode.PRIVATE) as body_box_bsketch:
            with Locations(body_locations):
                RectangleRounded(label_area.X, label_area.Y, label_area.Y / 10)
        body_box_sketch = body_box_bsketch.sketch

    base_part = base_bpart.part

    if not is_2d:
        logger.debug(f"BASE PART {base_part}\n{base_part.show_topology()}")
        if args.style == LabelStyle.DEBOSSED:
            # this produces "UserWarning: Unknown Compound type, color not set"; I don't know why
            base_part -= label_compound
            assembly = Compound(children=[base_part])
        else:
            assembly = Compound(children=[base_part, label_compound])
        base_part.label = "Base"
        base_part.color = Color(args.base_color)

    for output in args.output:
        if output.endswith(".stl"):
            logger.info(f"Writing STL {output}")
            export_stl(assembly, output)
        elif output.endswith(".step"):
            logger.info(f"Writing STEP {output}")
            export_step(assembly, output)
        elif output.endswith(".svg"):
            max_dimension = max(
                *label_compound.bounding_box().size, label_area.X, label_area.Y
            )
            exporter = ExportSVG(scale=100 / max_dimension)

            if args.box and is_2d:
                exporter.add_layer("Box", line_color=Color(args.base_color), line_weight=1)
                exporter.add_shape(body_box_sketch, layer="Box")
            if args.svg_mono:
                exporter.add_layer("Shapes", fill_color=Color(args.label_color), line_weight=0)
                compound_in_plane = label_compound.intersect(Plane.XY)
                exporter.add_shape(compound_in_plane, layer="Shapes")
            else:
                layer_dict = {}
                for pdex, part in enumerate(colored_parts(label_compound)):
                    color = part.color
                    color_str = str(color)
                    if not color_str in layer_dict:
                        exporter.add_layer(name=color_str, fill_color=color, line_weight=0)
                        layer_dict[color_str] = True
                    part_in_plane = part.intersect(Plane.XY)
                    exporter.add_shape(part_in_plane, layer=color_str)
            logger.info(f"Writing SVG {output}")
            exporter.write(output)
        else:
            logger.error(f"Error: Do not understand output format '{args.output}'")

    if args.vscode:
        if is_2d:
            show(label_compound)
        else:
            # Export both step and stl in vscode_ocp mode
            logger.info("Writing STL label.stl")
            bd.export_stl(assembly, "label.stl")
            logger.info("Writing STEP label.step")
            export_step(assembly, "label.step")

            if args.style != LabelStyle.DEBOSSED:
                # CAD viewer notices the Part colors
                show(assembly)
            else:
                # Split the base for display as two colours
                show_parts = []
                show_cols = []
                top = base_part.split(Plane.XY.offset(-args.depth), keep=Keep.TOP)
                if top:
                    show_parts.append(top)
                    show_cols.append(args.base_color)
                if args.base != "none":
                    bottom = base_part.split(Plane.XY, keep=Keep.BOTTOM)
                    if bottom:
                        show_parts.append(bottom)
                        show_cols.append(args.label_color)
                show(top, bottom, colors=show_cols)

if __name__ == "__main__":
    run()
