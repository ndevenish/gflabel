"""
Labels for "Modern Gridfinity Case"

https://www.printables.com/model/894202-modern-gridfinity-case
"""

from __future__ import annotations

import argparse
import math
import sys

from build123d import (
    Align,
    Axis,
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Locations,
    Mode,
    Plane,
    Polyline,
    Select,
    Vector,
    add,
    chamfer,
    extrude,
    make_face,
    mirror,
)

from . import LabelBase


class ModernBase(LabelBase):
    """
    Generate a Modern-Gridfinity-Case label body

    Origin is positioned at the center of the label, with the label
    surface at z=0.
    """

    def __init__(self, args: argparse.Namespace):
        # Temporary: Pull these out of the args without checking
        width = args.width
        height_mm = args.height

        EXTRA_WIDTH_TOL = 0.5
        EXTRA_INDENT_TOL = 0.4
        INDENT_DEPTH = 0.6 + 0.2
        KNOWN_WIDTHS = {3: 31.8, 4: 50.8, 5: 75.8, 6: 115.8, 7: 140.800, 8: 140.800}
        KNOWN_INDENT_WIDTHS = {
            3: 16,
            4: 35,
            5: 60,
            6: 100,
            7: 125,
            8: 125,
        }

        if width not in KNOWN_WIDTHS:
            sys.exit(
                f"Error: Do not know how wide to create 'modern' label for {width} u"
            )

        W = KNOWN_WIDTHS[width] - EXTRA_WIDTH_TOL
        H = height_mm or 22.117157  # I cannot work out the basis for this value
        depth = 2.2

        # Label constructed by angled extrusion of inner sketch
        W_inner = W - depth
        H_inner = H - depth

        with BuildPart() as part:
            with BuildSketch(Plane.XY.offset(amount=-depth / 2)) as _sketch:
                with BuildLine() as _line:
                    corner_length = 1.8
                    corner_off = corner_length * math.sin(math.pi / 4)
                    Polyline(
                        [
                            (0, -H_inner / 2),
                            (-W_inner / 2, -H_inner / 2),
                            (-W_inner / 2, H_inner / 2 - corner_off),
                            (-W_inner / 2 + corner_off, H_inner / 2),
                            (0, H_inner / 2),
                        ]
                    )
                    mirror(_line.line, Plane.YZ)
                make_face()
            extrude(amount=depth / 2, taper=-45, both=True)

            # Add the flattened base
            with BuildPart(mode=Mode.PRIVATE) as _bottom_part:
                with Locations([(0, -H / 2, -depth / 2)]):
                    Box(W, depth, depth, align=(Align.CENTER, Align.MIN, Align.CENTER))

                    edges = (
                        _bottom_part.edges(Select.LAST)
                        .filter_by(Axis.Z)
                        .group_by(Axis.Y)[-1]
                    )
                    chamfer(edges, length=1.2)
            add(_bottom_part.part)

            # Add the indent
            # 60mm x 13mm, 4.7m from bottom
            with Locations([(0, -H / 2 + 4.7, -depth)]):
                Box(
                    KNOWN_INDENT_WIDTHS[width] + EXTRA_INDENT_TOL,
                    13,
                    INDENT_DEPTH,
                    mode=Mode.SUBTRACT,
                    align=(Align.CENTER, Align.MIN, Align.MIN),
                )

        self.part = part.part
        self.area = Vector(W, H)
