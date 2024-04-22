from __future__ import annotations

from typing import NamedTuple

from build123d import Part, Vector


class LabelBase(NamedTuple):
    """
    Output object from base creation.
    """

    part: Part
    area: Vector
