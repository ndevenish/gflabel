"""
Labels for "Modern Gridfinity Case"

https://www.printables.com/model/894202-modern-gridfinity-case
"""

from __future__ import annotations

import argparse
import logging
import math
import sys

import pint
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

from ..util import unit_registry
from . import LabelBase

logger = logging.getLogger(__name__)


class ModernBase(LabelBase):
    """
    Generate a Modern-Gridfinity-Case label body

    Origin is positioned at the center of the label, with the label
    surface at z=0.
    """

    def __init__(self, args: argparse.Namespace):
        # Temporary: Pull these out of the args without checking
        # width = args.width
        # height_mm = args.height

        KNOWN_WIDTHS = {3: 31.8, 4: 50.8, 5: 75.8, 6: 115.8, 7: 140.800, 8: 140.800}
        # Tolerance factor to shrink the width by
        EXTRA_WIDTH_TOL = 0.5

        # The indent is 15.8mm narrower than the label width
        INDENT_WIDTH_MARGINS = 15.8
        # Tolerance factor to enlarge the indent width by
        EXTRA_INDENT_TOL = 0.4
        INDENT_DEPTH = 0.6 + 0.2

        def _convert_u_to_mm(u: pint.Quantity):
            if u.magnitude not in KNOWN_WIDTHS:
                logger.error(
                    "'Modern' label u-dimensions only known for 3u-8u boxes. Specify mm for custom sizes."
                )
                sys.exit(1)
            return pint.Quantity(
                KNOWN_WIDTHS[u.magnitude] - EXTRA_WIDTH_TOL,
                "mm",
            )

        with unit_registry.context("u", fn=_convert_u_to_mm):
            W_mm = args.width.to("mm").magnitude
        H_mm = 22.117157  # I cannot work out the basis for this value
        if args.height is not None:
            H_mm = args.height.to("mm").magnitude

        depth = 2.2

        # Label constructed by angled extrusion of inner sketch
        W_inner = W_mm - depth
        H_inner = H_mm - depth

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
                with Locations([(0, -H_mm / 2, -depth / 2)]):
                    Box(
                        W_mm,
                        depth,
                        depth,
                        align=(Align.CENTER, Align.MIN, Align.CENTER),
                    )

                    edges = (
                        _bottom_part.edges(Select.LAST)
                        .filter_by(Axis.Z)
                        .group_by(Axis.Y)[-1]
                    )
                    chamfer(edges, length=1.2)
            add(_bottom_part.part)

            # Add the indent
            # 60mm x 13mm, 4.7m from bottom
            with Locations([(0, -H_mm / 2 + 4.7, -depth)]):
                Box(
                    W_mm - INDENT_WIDTH_MARGINS + EXTRA_INDENT_TOL,
                    13,
                    INDENT_DEPTH,
                    mode=Mode.SUBTRACT,
                    align=(Align.CENTER, Align.MIN, Align.MIN),
                )

        self.part = part.part
        self.area = Vector(W_mm, H_mm)
