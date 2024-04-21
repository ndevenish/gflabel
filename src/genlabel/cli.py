#!/usr/bin/env python3
# ruff: noqa: F403

from __future__ import annotations

import functools
import logging
import re
from argparse import ArgumentParser
from collections.abc import Callable, Sequence
from itertools import islice
from math import cos, pi, radians, sin, tan

import build123d as bd

# from build123d import *
from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    CenterArc,
    Circle,
    FilletPolyline,
    FontStyle,
    Location,
    Locations,
    Mode,
    Part,
    Plane,
    Polyline,
    RegularPolygon,
    Sketch,
    Text,
    add,
    export_step,
    extrude,
    fillet,
    make_face,
    mirror,
)
from ocp_vscode import Camera, set_defaults, show

logger = logging.getLogger(__name__)

set_defaults(reset_camera=Camera.CENTER)


# Taken from Python 3.12 documentation.
def batched(iterable, n):
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def _outer_edge(width_u: int) -> Sketch:
    # Width of straight bit in label is:
    #   Bin width (u * 42)
    # - label margins (4.2mm)
    # - label end size (1.9mm per end)
    straight_width = width_u * 42 - 4.2 - (1.9 * 2)
    with BuildSketch() as sketch:
        with BuildLine() as line:
            # Where the sketch is placed in X. 2.1 is the pred label offset
            # on one edge; 1.9 is the extra distance to our "zero" point
            # x = 2.1 + 1.9
            x = -straight_width / 2
            l1 = Polyline([(x - 1.9, 0), (x - 1.9, 2.85), (x - 0.9, 2.85)])
            FilletPolyline(
                [
                    l1 @ 1,
                    (x - 0.9, 5.75),
                    (0, 5.75),
                ],
                radius=0.9,
            )
            mirror(line.line, Plane.XZ)
            mirror(line.line, Plane.YZ)

        make_face()

        with Locations([(x - 0.4, 0, 0.4), (x + straight_width + 0.4, 0, 0.4)]):
            Circle(0.75, mode=Mode.SUBTRACT)

    return sketch.sketch


def _inner_edge(width_u: int) -> Sketch:
    straight_width = width_u * 42 - 4.2 - (1.9 * 2)
    x = -straight_width / 2
    with BuildSketch() as sketch:
        with BuildLine() as line:
            a1 = CenterArc((x - 0.4, 0), 1.25, 0, 90)
            FilletPolyline([a1 @ 1, (x - 0.4, 5.25), (0, 5.25)], radius=0.4)
            # Fillet the vertex between the arc and polyline
            fillet([line.vertices().sort_by_distance(a1 @ 1)[0]], radius=1)
            mirror(line.line, Plane.XZ)
            mirror(line.line, Plane.YZ)
        make_face()

    return sketch.sketch


def make_label_body(width_u: int) -> Part:
    with BuildPart() as part:
        add(_outer_edge(width_u=width_u))
        # Extrude the base up
        extrude(amount=0.4, both=True)

        add(_inner_edge(width_u=width_u))
        # Cut the indent out of the top face
        extrude(amount=0.4, mode=Mode.SUBTRACT)

        # 0.2 mm fillet all top edges
        fillet_edges = [
            *part.edges().group_by(Axis.Z)[-1],
            *part.edges().group_by(Axis.Z)[0],
        ]
        fillet(fillet_edges, radius=0.2)
    return part.part


def _fragment_hexhead(height: float, _maxsize: float) -> Sketch:
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
        RegularPolygon(height / 2 * 0.6, side_count=6, mode=Mode.SUBTRACT)
    return sketch.sketch


def _fragment_hexnut(height: float, _maxsize: float) -> Sketch:
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        RegularPolygon(height / 2, side_count=6)
        Circle(height / 2 * 0.4, mode=Mode.SUBTRACT)
    return sketch.sketch


def _fragment_washer(height: float, _maxsize: float) -> Sketch:
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
        Circle(height / 2 * 0.4, mode=Mode.SUBTRACT)
    return sketch.sketch


def _fragment_bolt(length: float | str, height: float, maxsize: float) -> Sketch:
    length = float(length)
    # line width: How thick the head and body are
    lw = height / 2.25
    # The half-width of the dividing split
    half_split = 0.75

    # Don't allow lengths smaller than lw
    # length = max(length, lw * 2 + half_split)
    maxsize = max(maxsize, lw * 2 + half_split * 2 + 0.1)
    # Work out what the total length is, and if this is over max size
    # then we need to cut the bolt
    split_bolt = length + lw > maxsize
    # Halfwidth distance
    if split_bolt:
        hw = maxsize / 2
    else:
        hw = (length + lw) / 2

    if not split_bolt:
        with BuildSketch(mode=Mode.PRIVATE) as sketch:
            with BuildLine() as line:
                Polyline(
                    [
                        (-hw, 0),
                        (-hw, height / 2),
                        (-hw + lw, height / 2),
                        (-hw + lw, lw / 2),
                        (hw, lw / 2),
                        (hw, 0),
                    ],
                )
                mirror(line.line, Plane.XZ)
            make_face()
    else:
        # We need to split the bolt
        with BuildSketch(mode=Mode.PRIVATE) as sketch:
            x_shaft_midpoint = lw + (maxsize - lw) / 2 - hw
            with BuildLine() as line:
                Polyline(
                    [
                        (-hw, height / 2),
                        (-hw + lw, height / 2),
                        (-hw + lw, lw / 2),
                        # Divider is halfway along the shaft
                        (x_shaft_midpoint + lw / 2 - half_split, lw / 2),
                        (x_shaft_midpoint - lw / 2 - half_split, -lw / 2),
                        (-hw + lw, -lw / 2),
                        (-hw + lw, -height / 2),
                        (-hw, -height / 2),
                    ],
                    close=True,
                )
            make_face()
            with BuildLine() as line:
                Polyline(
                    [
                        # Divider is halfway along the shaft
                        (x_shaft_midpoint + lw / 2 + half_split, lw / 2),
                        (hw, lw / 2),
                        (hw, -lw / 2),
                        (x_shaft_midpoint - lw / 2 + half_split, -lw / 2),
                    ],
                    close=True,
                )
            make_face()
    return sketch.sketch


def _fragment_variable_resistor(height: float, maxsize: float) -> Sketch:
    # symb = import_svg("symbols/variable_resistor.svg")
    t = 0.4 / 2
    w = 6.5
    h = 2
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        # add(symb)
        # Circle(1)
        # sweep(symb)
        with BuildLine():
            Polyline(
                [
                    (-6, 0),
                    (-6, t),
                    (-w / 2 - t, t),
                    (-w / 2 - t, h / 2 + t),
                    (0, h / 2 + t),
                    (0, h / 2 - t),
                    (-w / 2 + t, h / 2 - t),
                    (-w / 2 + t, 0),
                ],
                close=True,
            )
        make_face()
        mirror(sketch.sketch, Plane.XZ)
        mirror(sketch.sketch, Plane.YZ)

        # with BuildLine():
        l_arr = 7
        l_head = 1.5
        angle = 30

        theta = radians(angle)
        oh = t / tan(theta) + t / sin(theta)
        sigma = pi / 2 - theta
        l_short = t / cos(sigma)
        #     l_arrow = 1.5
        #     angle = 30
        #     # Work out the intersect height
        #     h_i = t / math.sin(math.radians(angle))
        #     arr_bottom_lost = t / math.tan(math.radians(angle))
        arrow_parts = [
            (0, -l_arr / 2),
            (-t, -l_arr / 2),
            (-t, l_arr / 2 - oh),
            (
                -t - sin(theta) * (l_head - l_short),
                l_arr / 2 - oh - cos(theta) * (l_head - l_short),
            ),
            (-sin(theta) * l_head, l_arr / 2 - cos(theta) * l_head),
            (0, l_arr / 2),
            # (0, -l_arr / 2),
        ]
        with BuildSketch(mode=Mode.PRIVATE) as arrow:
            with BuildLine() as line:
                Polyline(
                    arrow_parts,
                    # close=True,
                )
                mirror(line.line, Plane.YZ)
            make_face()
        add(arrow.sketch.rotate(Axis.Z, -30))
        # sketch.sketch.rotate(Axis.Z, 20)
        # with BuildLine() as line:
        #     Line([(0, -arr_h / 2), (0, arr_h / 2)])
        # Arrow(arr_h, line, t * 2, head_at_start=False)
        # mirror(line.line, Plane.XZ)
        # mirror(line.line, Plane.YZ)
        # offset(symb, amount=1)
        # add(symb)
    # Scale to fit in our height, unless this would take us over width
    size = sketch.sketch.bounding_box().size
    scale = height / size.Y
    # actual_w = min(scale * size.X, maxsize)
    # scale = actual_w / size.X

    return sketch.sketch.scale(scale)


_FRAGMENTS = {
    "hexhead": _fragment_hexhead,
    "bolt": _fragment_bolt,
    "washer": _fragment_washer,
    "hexnut": _fragment_hexnut,
    "nut": _fragment_hexnut,
    "variable_resistor": _fragment_variable_resistor,
}


def _parse_fragment(fragment: str) -> float | Callable[[float, float], Sketch]:
    # If a numeric fragment, we just want a spacer
    try:
        return float(fragment)
    except ValueError:
        pass
    # If directly named, then just return the generator
    if fragment in _FRAGMENTS:
        return _FRAGMENTS[fragment]
    name, argstr = re.match(r"(.+?)(?:\((.*)\))?$", fragment).groups()
    args = argstr.split(",") if argstr else []
    if name not in _FRAGMENTS:
        raise RuntimeError(f"Unknown fragment class: {name}")
    return functools.partial(_FRAGMENTS[name], *args)


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

    per_bin_width = (42 * width - 4.2 - 5.5) / max(divisions, 1)
    _leftmost_label = -(per_bin_width * divisions) / 2 + per_bin_width / 2

    with BuildPart() as part:
        add(make_label_body(width_u=width))
        if divisions:
            with BuildSketch() as _sketch:
                for i, label in zip(range(divisions), labels):
                    with Locations([(_leftmost_label + per_bin_width * i, 0)]):
                        add(make_text_label(label, per_bin_width))

            extrude(amount=0.4)
    return part.part


def run(argv: list[str] | None = None):
    parser = ArgumentParser(description="Generate pred-style gridfinity bin labels")
    parser.add_argument("width", help="Label width, in units", metavar="WIDTH_U")
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
