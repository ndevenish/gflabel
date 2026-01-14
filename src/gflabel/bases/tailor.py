from __future__ import annotations

import argparse
import logging
import sys

import pint
from build123d import (
    BuildPart,
    BuildSketch,
    Plane,
    RectangleRounded,
    Vector,
    chamfer,
    extrude,
)

from ..util import unit_registry
from . import LabelBase

logger = logging.getLogger(__name__)


class TailorBoxBase(LabelBase):
    DEFAULT_WIDTH = pint.Quantity("5u")
    DEFAULT_WIDTH_UNIT = unit_registry.u
    DEFAULT_MARGIN = unit_registry.Quantity(3, "mm")

    def __init__(self, args: argparse.Namespace):
        def _convert_u_to_mm(u: pint.Quantity):
            if args.width.magnitude not in {5}:
                logger.error("Tailor box only known for 5u boxes")
                sys.exit(1)
            return pint.Quantity(
                {
                    5: 96.75,
                }[u.magnitude],
                "mm",
            )

        with unit_registry.context("u", fn=_convert_u_to_mm):
            width_mm = args.width.to("mm").magnitude

        r_edge = 3.5
        depth = 1.25
        chamfer_d = 0.2
        height_mm = 24.8
        if args.height is not None:
            height_mm = args.height.to("mm").magnitude

        with BuildPart() as part:
            with BuildSketch() as sketch:
                RectangleRounded(width_mm, height_mm, r_edge)
            extrude(sketch.sketch, -depth)

            chamfer(part.faces().filter_by(Plane.XY).edges(), chamfer_d)

        self.part = part.part
        self.area = Vector(width_mm - chamfer_d * 2, height_mm - chamfer_d * 2)
