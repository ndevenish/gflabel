from __future__ import annotations

import logging
from math import cos, pi, radians, sin, tan

from build123d import (
    Axis,
    BuildLine,
    BuildSketch,
    Circle,
    Mode,
    Plane,
    Polyline,
    RegularPolygon,
    Sketch,
    add,
    make_face,
    mirror,
)

logger = logging.getLogger(__name__)

FRAGMENTS = {}


def fragment(*names):
    """Register a label fragment generator"""

    def _wrapped(fn):
        for name in names:
            print(f"Registering fragment {name} = {fn}")
            FRAGMENTS[name] = fn
        return fn

    return _wrapped


class Fragment:
    pass


@fragment("hexhead")
def _fragment_hexhead(height: float, _maxsize: float) -> Sketch:
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
        RegularPolygon(height / 2 * 0.6, side_count=6, mode=Mode.SUBTRACT)
    return sketch.sketch


@fragment("hexnut", "nut")
def _fragment_hexnut(height: float, _maxsize: float) -> Sketch:
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        RegularPolygon(height / 2, side_count=6)
        Circle(height / 2 * 0.4, mode=Mode.SUBTRACT)
    return sketch.sketch


@fragment("washer")
def _fragment_washer(height: float, _maxsize: float) -> Sketch:
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
        Circle(height / 2 * 0.4, mode=Mode.SUBTRACT)
    return sketch.sketch


@fragment("bolt")
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


@fragment("variable_resistor")
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
