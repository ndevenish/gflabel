"""
Code for rendering a label from a label definition.
"""

from __future__ import annotations

import functools
import logging
import re
from collections.abc import Callable, Sequence
from typing import NamedTuple

from build123d import (
    BuildPart,
    BuildSketch,
    FontStyle,
    Locations,
    Mode,
    Part,
    Sketch,
    Text,
    Vector,
    add,
    extrude,
)

from . import fragments
from .bases import pred

logger = logging.getLogger(__name__)

RE_FRAGMENT = re.compile(r"((?<!{){[^{}]+})")


class RenderOptions(NamedTuple):
    line_spacing_mm: float = 0.1


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


def _spec_to_fragments(spec: str) -> list[fragments.Fragment]:
    """Convert a single line spec string to a list of renderable fragments."""
    fragments = []
    for part in RE_FRAGMENT.split(spec):
        if part.startwith("{") and not part.startswith("{") and part.endswith("}"):
            # We have a special fragment. Find and instantiate it.
            pass
        else:
            # We have text. Build123d Text object doesn't handle leading/
            # trailing spaces, so let's split them out here and put in
            # explicit whitespace fragments
            pass


class LabelRenderer:
    def __init__(self, options: RenderOptions):
        self.opts = options

    def render(self, spec: str, area: Vector) -> Sketch:
        """
        Given a specification string, render a single label.

        Args:
            spec: The string representing the label.
            area: The width and height the label should be confined to.

        Returns:
            A rendered Sketch object with the label contents, centered on
            the origin.
        """
        lines = spec.splitlines()

        if not lines:
            raise ValueError("Asked to render empty label")

        row_height = area.Y - (self.opts.line_spacing_mm * (len(lines) - 1)) / len(
            lines
        )

        with BuildSketch() as sketch:
            # Render each line onto the sketch separately
            for n, line in enumerate(lines):
                # Calculate the y of the line center
                render_y = (
                    area.Y / 2
                    - (row_height + self.opts.line_spacing_mm) * n
                    - row_height / 2
                )
                with Locations([(0, render_y)]):
                    add(self._render_single_line(line, Vector(x=area.X, y=row_height)))

        return sketch.sketch

    def _render_single_line(self, line: str, area: Vector):
        """
        Render a single line of a labelspec.
        """
        # Firstly, split the line into a set of fragment objects


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
