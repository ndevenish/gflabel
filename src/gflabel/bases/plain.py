from __future__ import annotations

from build123d import Axis, BuildPart, BuildSketch, Rectangle, Vector, extrude, fillet

from . import LabelBase


def body(width_mm: float, height: float, recessed: bool = True) -> LabelBase:
    """
    Generate a plain-label body.

    Origin is positioned at the center of the label, with the label
    surface at z=0.

    Args:
        width_mm: The width of the label.
        recessed:
            Whether the label surface is resecced into the label (used
            for embossing) or just flat, for cutting away.

    Returns:
        A LabelBase tuple consisting of:
            part: The actual label body.
            label_area: A vector describing the width, height of the usable area.
    """

    with BuildPart() as part:
        with BuildSketch() as _sketch:
            Rectangle(width_mm, height=height)
        # Extrude the base up
        extrude(amount=-0.8)

        # if recessed:
        #     add(_inner_edge(width_u=width_u))
        #     # Cut the indent out of the top face
        #     extrude(amount=0.4, mode=Mode.SUBTRACT)

        # 0.2 mm fillet all top edges
        fillet_edges = [
            *part.edges().group_by(Axis.Z)[-1],
            # *part.edges().group_by(Axis.Z)[0],
        ]
        fillet(fillet_edges, radius=0.2)

    return LabelBase(part.part, Vector(width_mm, height))
