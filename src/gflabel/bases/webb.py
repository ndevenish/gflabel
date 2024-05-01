from __future__ import annotations

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Mode,
    Plane,
    Polyline,
    RectangleRounded,
    Vector,
    extrude,
    make_face,
)

from . import LabelBase


def body() -> LabelBase:
    """
    Generate a Webb-style label body

    Origin is positioned at the center of the label, with the label
    surface at z=0.

    Returns:
        A LabelBase tuple consisting of:
            part: The actual label body.
            label_area: A vector describing the width, height of the usable area.
    """
    width = 36.4
    height = 11
    depth = 1
    with BuildPart() as part:
        with BuildSketch():
            RectangleRounded(width=width, height=height, radius=0.5)

        extrude(amount=-depth)

        # Plane.XZ
        with BuildSketch(Plane.XZ) as _sketch:
            for x in [-12.133, 0, 12.133]:
                with BuildLine(Plane.XZ) as _line:
                    Polyline(
                        [
                            (x - 0.75, -0.4),
                            (x - 0.5, -1),
                            (x + 0.5, -1),
                            (x + 0.75, -0.4),
                        ],
                        close=True,
                    )
                make_face()
        extrude(amount=height / 2, both=True, mode=Mode.SUBTRACT)

    return LabelBase(part.part, Vector(36.4, 11))
