"""
Code for rendering a label from a label definition.
"""

from __future__ import annotations

import logging
import re

from build123d import (
    BuildSketch,
    Locations,
    Sketch,
    Vector,
    add,
)
from rich import print

from . import fragments
from .options import RenderOptions

logger = logging.getLogger(__name__)

RE_FRAGMENT = re.compile(r"((?<!{){[^{}]+})")


def _spec_to_fragments(spec: str) -> list[fragments.Fragment]:
    """Convert a single line spec string to a list of renderable fragments."""
    fragment_list = []
    for part in RE_FRAGMENT.split(spec):
        if part.startswith("{") and not part.startswith("{{") and part.endswith("}"):
            # We have a special fragment. Find and instantiate it.
            fragment_list.append(fragments.fragment_from_spec(part[1:-1]))
        else:
            # We have text. Build123d Text object doesn't handle leading/
            # trailing spaces, so let's split them out here and put in
            # explicit whitespace fragments
            part = part.replace("{{", "{").replace("}}", "}")
            left_spaces = part[: len(part) - len(part.lstrip())]
            if left_spaces:
                fragment_list.append(fragments.WhitespaceFragment(left_spaces))
            part = part.lstrip()

            part_stripped = part.strip()
            if part_stripped:
                fragment_list.append(fragments.TextFragment(part_stripped))

            if chars := len(part) - len(part_stripped):
                fragment_list.append(fragments.WhitespaceFragment(part[-chars:]))
    return fragment_list


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
        return self._do_multiline_render(spec, area)

    def _do_multiline_render(
        self, spec: str, area: Vector, is_rescaling: bool = False
    ) -> Sketch:
        """Label render function, with ability to recurse."""
        lines = spec.splitlines()

        if not lines:
            raise ValueError("Asked to render empty label")

        row_height = (area.Y - (self.opts.line_spacing_mm * (len(lines) - 1))) / len(
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
                print(f"Rendering line {n} ({line}) at {render_y})")
                with Locations([(0, render_y)]):
                    add(
                        self._render_single_line(
                            line,
                            Vector(X=area.X, Y=row_height),
                            self.opts.allow_overheight,
                        )
                    )

        scale_to_maxwidth = area.X / sketch.sketch.bounding_box().size.X
        scale_to_maxheight = area.Y / sketch.sketch.bounding_box().size.Y
        if scale_to_maxheight < 1:
            print(
                f"Vertical scale is too high for area ({scale_to_maxheight}); downscaling"
            )
        to_scale = min(scale_to_maxheight, scale_to_maxwidth, 1)
        print(f"Got scale: {to_scale}")
        if to_scale < 0.99 and not is_rescaling:
            print(f"Rescaling as {scale_to_maxwidth}")
            # We need to scale this down. Resort to adjusting the height and re-requesting.
            # second = make_text_label(
            #     spec,
            #     maxwidth,
            #     maxheight=maxheight * scale_to_maxwidth * 0.95,
            #     _rescaling=True,
            # )
            second_try = self._do_multiline_render(
                spec,
                Vector(X=area.X, Y=area.Y * to_scale * 0.95),
                is_rescaling=True,
            )
            # If this didn't help, then error
            if (bbox_w := second_try.bounding_box().size.X) > area.X:
                logger.warning(
                    'Warning: Could not fit label "%s" in box of width %.2f, got %.1f',
                    spec,
                    area.X,
                    bbox_w,
                )
            print(
                f'Entry "{spec}" calculated width = {sketch.sketch.bounding_box().size.X:.1f} (max {area.X})'
            )
            return second_try
        print(
            f'Entry "{spec}" calculated width = {sketch.sketch.bounding_box().size.X:.1f} (max {area.X})'
        )

        return sketch.sketch

    def _render_single_line(
        self, line: str, area: Vector, allow_overheight: bool
    ) -> Sketch:
        """
        Render a single line of a labelspec.
        """
        # Firstly, split the line into a set of fragment objects
        frags = _spec_to_fragments(line)

        # Overheight fragments: Work out if we have any, so that we can
        # scale the total height such that they fit.
        # If this isn't turned on, then we will still allow the fragment
        # to be overheight but it will be given a smaller vertical area
        # such that the overheight fits in the line.
        options = self.opts._replace(allow_overheight=allow_overheight)
        Y_available = area.Y
        if allow_overheight:
            max_overheight = max(x.overheight or 1 for x in frags)
            if max_overheight > 1:
                Y_available /= max_overheight
                print(
                    f"Scaling Y area to account for overheight from {area.Y:.2f} -> {Y_available:.2f}"
                )

        rendered: dict[fragments.Fragment, Sketch] = {}
        for frag in [x for x in frags if not x.variable_width]:
            # Handle overheight if we have overheight turned off
            frag_available_y = Y_available / (
                1 if allow_overheight else (frag.overheight or 1)
            )
            rendered[frag] = frag.render(frag_available_y, area.X, self.opts)

        # Work out what we have left to give to the variable labels
        remaining_area = area.X - sum(
            x.bounding_box().size.X for x in rendered.values()
        )
        count_variable = len(frags) - len(rendered)

        # Render the variable-width labels.
        # For now, very dumb algorithm: Each variable fragment gets w/N.
        # but we recalculate after each render.
        for frag in sorted(
            [x for x in frags if x.variable_width],
            key=lambda x: x.priority,
            reverse=True,
        ):
            # Handle overheight if we have overheight turned off
            frag_available_y = Y_available / (
                1 if allow_overheight else (frag.overheight or 1)
            )
            render = frag.render(
                frag_available_y,
                max(remaining_area / count_variable, frag.min_width(area.Y)),
                options,
            )
            rendered[frag] = render
            count_variable -= 1
            remaining_area -= render.bounding_box().size.X

        # Calculate the total width
        total_width = sum(x.bounding_box().size.X for x in rendered.values())
        if total_width > area.X:
            logger.warning("Overfull Hbox: Label is wider than available area")

        # Assemble these onto the target
        with BuildSketch() as sketch:
            x = -total_width / 2
            for fragment, frag_sketch in [(x, rendered[x]) for x in frags]:
                fragment_width = frag_sketch.bounding_box().size.X
                with Locations((x + fragment_width / 2, 0)):
                    if fragment.visible:
                        add(frag_sketch)
                x += fragment_width

        return sketch.sketch


def render_divided_label(
    labels: str, area: Vector, divisions: int, options: RenderOptions
) -> Sketch:
    """
    Create a sketch for multiple labels fitted into a single area
    """
    area = Vector(X=area.X - options.margin_mm * 2, Y=area.Y - options.margin_mm * 2)
    area_per_label = Vector(area.X / divisions, area.Y)
    leftmost_label_x = -area.X / 2 + area_per_label.X / 2
    renderer = LabelRenderer(options)
    with BuildSketch() as sketch:
        for i, label in enumerate(labels):
            with Locations([(leftmost_label_x + i * area_per_label.X, 0)]):
                if label.strip():
                    add(renderer.render(label, area_per_label))

    return sketch.sketch
