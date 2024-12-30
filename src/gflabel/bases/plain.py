from __future__ import annotations

import argparse

from build123d import Axis, BuildPart, BuildSketch, Rectangle, Vector, extrude, fillet

from . import LabelBase


class PlainBase(LabelBase):
    """
    Generate a plain-label body.

    Origin is positioned at the center of the label, with the label
    surface at z=0.

    Args:
        width_mm: The width of the label.
        recessed:
            Whether the label surface is resecced into the label (used
            for embossing) or just flat, for cutting away.

    """

    def __init__(self, args: argparse.Namespace):
        width_mm = args.width
        height = args.height
        with BuildPart() as part:
            with BuildSketch() as _sketch:
                Rectangle(width_mm, height=height)
            # Extrude the base up
            extrude(amount=-0.8)

            # 0.2 mm fillet all top edges
            fillet_edges = [
                *part.edges().group_by(Axis.Z)[-1],
                # *part.edges().group_by(Axis.Z)[0],
            ]
            fillet(fillet_edges, radius=0.2)

        self.part = part.part
        self.area = Vector(width_mm, height)
