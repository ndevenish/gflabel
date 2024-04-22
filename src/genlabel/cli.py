#!/usr/bin/env python3
# ruff: noqa: F403

from __future__ import annotations

import functools
import logging
import re
from argparse import ArgumentParser
from collections.abc import Callable, Sequence
from itertools import islice

import build123d as bd

# from build123d import *
from build123d import (
    BuildPart,
    BuildSketch,
    FontStyle,
    Location,
    Locations,
    Mode,
    Part,
    Sketch,
    Text,
    add,
    export_step,
    extrude,
)
from ocp_vscode import Camera, set_defaults, show

from . import fragments
from .bases import pred

logger = logging.getLogger(__name__)

# logging.basicConfig(level=logging.DEBUG)
set_defaults(reset_camera=Camera.CENTER)


# Taken from Python 3.12 documentation.
def batched(iterable, n):
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def _parse_fragment(fragment: str) -> float | Callable[[float, float], Sketch]:
    # If a numeric fragment, we just want a spacer
    try:
        return float(fragment)
    except ValueError:
        pass
    # If directly named, then just return the generator
    if fragment in fragments.FRAGMENTS:
        return fragments.FRAGMENTS[fragment]
    name, argstr = re.match(r"(.+?)(?:\((.*)\))?$", fragment).groups()
    args = argstr.split(",") if argstr else []
    if name not in fragments.FRAGMENTS:
        raise RuntimeError(f"Unknown fragment class: {name}")
    return functools.partial(fragments.FRAGMENTS[name], *args)


def split_linespec_string(
    line: str,
) -> Sequence[float | str | Callable[[float, float], Sketch]]:
    parts = []
    part: str
    for part in re.split(r"((?<!{){[^{}]+})", line):
        if part.startswith("{") and not part.startswith("{{") and part.endswith("}"):
            parts.append(_parse_fragment(part[1:-1]))
        else:
            # Leading and trailing whitepace are split on their own
            left_spaces = part[: len(part) - len(part.lstrip())]
            if left_spaces:
                parts.append(left_spaces)
            part = part.lstrip()

            part_stripped = part.strip()
            if part_stripped:
                parts.append(part_stripped)

            if chars := len(part) - len(part_stripped):
                parts.append(part[-chars:])
    return parts


@functools.lru_cache
def _space_width(spacechar: str, height: float) -> float:
    """Calculate the width of a space at a specific text height"""
    w2 = (
        Text(
            f"a{spacechar}a",
            height,
            font="Futura",
            font_style=FontStyle.BOLD,
            mode=Mode.PRIVATE,
        )
        .bounding_box()
        .size.X
    )
    wn = (
        Text(
            "aa",
            height,
            font="Futura",
            font_style=FontStyle.BOLD,
            mode=Mode.PRIVATE,
        )
        .bounding_box()
        .size.X
    )
    return w2 - wn


def make_line_label(spec: str, height: float, maxwidth: float) -> Sketch:
    fragments: list[Sketch | float] = []
    for part in split_linespec_string(spec):
        if isinstance(part, str):
            if part.isspace():
                gap_width = sum(_space_width(x, height) for x in part)
                fragments.append(gap_width)
                maxwidth -= gap_width
            else:
                with BuildSketch(mode=Mode.PRIVATE):
                    text = Text(
                        part,
                        height,
                        font="Futura",
                        font_style=FontStyle.BOLD,
                    )
                    fragments.append(text)
                    maxwidth -= text.bounding_box().size.X
        elif isinstance(part, float):
            fragments.append(part)
            maxwidth -= part
        else:
            created_part = part(height, maxwidth)
            fragments.append(created_part)
            maxwidth -= created_part.bounding_box().size.X

    # Now, work out the width of all fragments
    # width = sum(Sketch. for x in fragments)
    width = sum(
        x if isinstance(x, float) else x.bounding_box().size.X for x in fragments
    )
    # Now, build the output sketch centered
    x = -width / 2
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        for part in fragments:
            if isinstance(part, float):
                x += part
                continue
            part_width = part.bounding_box().size.X
            with Locations((x + part_width / 2, 0)):
                add(part)
            x += part_width
    return sketch.sketch


def make_text_label(
    spec: str, maxwidth: float, maxheight: float = 9.5, _rescaling: bool = False
) -> Sketch:
    LINE_SEPARATOR = 0
    lines = spec.splitlines()
    # Work out how high we have for a single line
    height = (maxheight - LINE_SEPARATOR * (len(lines) - 1)) / len(lines)
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        for i, line in enumerate(lines):
            y = (maxheight / 2) - i * (height + LINE_SEPARATOR) - height / 2
            with Locations([(0, y)]):
                add(make_line_label(line, height, maxwidth))

    scale_to_maxwidth = maxwidth / sketch.sketch.bounding_box().size.X
    if scale_to_maxwidth < 0.99 and not _rescaling:
        print(f"Rescaling as {scale_to_maxwidth}")
        # We need to scale this down. Resort to adjusting the height and re-requesting.
        second = make_text_label(
            spec,
            maxwidth,
            maxheight=maxheight * scale_to_maxwidth * 0.95,
            _rescaling=True,
        )
        # If this didn't help, then error
        if (bbox_w := second.bounding_box().size.X) > maxwidth:
            logger.warning(
                'Warning: Could not fit label "%s" in box of width %.2f, got %.1f',
                spec,
                maxwidth,
                bbox_w,
            )
        print(
            f'Entry "{spec}" calculated width = {sketch.sketch.bounding_box().size.X:.1f} (max {maxwidth})'
        )
        return second
    print(
        f'Entry "{spec}" calculated width = {sketch.sketch.bounding_box().size.X:.1f} (max {maxwidth})'
    )
    return sketch.sketch


def generate_single_label(width: int, divisions: int, labels: list[str]) -> Part:
    labels = [x.replace("\\n", "\n") for x in labels]

    with BuildPart() as part:
        label_body = pred.body(width_u=width)
        add(label_body.part)

        per_bin_width = label_body.area.X / max(divisions, 1)
        _leftmost_label = -(per_bin_width * divisions) / 2 + per_bin_width / 2

        if divisions:
            with BuildSketch() as _sketch:
                for i, label in zip(range(divisions), labels):
                    with Locations([(_leftmost_label + per_bin_width * i, 0)]):
                        add(
                            make_text_label(
                                label, per_bin_width, maxheight=label_body.area.Y
                            )
                        )

            extrude(amount=0.4)
    return part.part


def run(argv: list[str] | None = None):
    parser = ArgumentParser(description="Generate pred-style gridfinity bin labels")
    parser.add_argument(
        "-w",
        "--width",
        help="Label width, in gridfinity units. Default: %(default)s",
        metavar="WIDTH_U",
        default="1",
    )
    parser.add_argument("labels", nargs="*", metavar="LABEL")
    parser.add_argument(
        "-d",
        "--divisions",
        help="How many areas to divide a single label into. If more labels that this are requested, multiple labels will be generated.",
        type=int,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename. [Default: %(default)s]",
        default="label.step",
    )
    args = parser.parse_args(argv)

    args.width = int(args.width.rstrip("u"))
    args.divisions = args.divisions or len(args.labels)

    y = 0
    with BuildPart() as part:
        for labels in batched(args.labels, args.divisions):
            label = generate_single_label(args.width, args.divisions, labels)
            label.location = Location((0, y))
            add(label)
            y -= 13

    if args.output.endswith(".stl"):
        bd.export_stl(part.part, args.output)
    elif args.output.endswith(".step"):
        export_step(part.part, args.output)
    else:
        print(f"Error: Do not understand output format '{args.output}'")

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
