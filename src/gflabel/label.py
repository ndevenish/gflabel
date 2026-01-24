"""
Code for rendering a label from a label definition.
"""

from __future__ import annotations

import logging
import re

from collections.abc import Callable
from build123d import (
    BuildPart,
    BuildSketch,
    Compound,
    Location,
    Locations,
    Mode,
    Part,
    Sketch,
    Vector,
    add,
    extrude,
)
from rich import print
from enum import Enum, auto

from . import fragments
from .options import RenderOptions, LabelStyle
from .util import IndentingRichHandler, batched

logger = logging.getLogger(__name__)

RE_FRAGMENT = re.compile(r"((?<!{){[^{}]+})")

# The nesting of logic here is:
#   Labels (overall collection from command line)
#     Batch (via the "-d" command line option)
#       Multiline (for possible embedded newlines)
#         Lines
#           Fragments (Part labels are computed from the fragment type)

# We extrude fragments into Parts at the very lowest level. We
# aggregate them into Compounds (with children) move up the stack.

# This label dictionary is a global to try to give unique
# labels in the entire batch of gflabels. Although unique,
# some numbers might be discarded due to rescaling in the
# rendering logic.
label_dict: dict[str, int] = {}

def get_global_label(candidate: str):
    label_count = label_dict[candidate] if (candidate in label_dict) else 0
    label_count += 1
    label_dict[candidate] = label_count
    unique = candidate + "_" + str(label_count)
    return unique
    
def clean_up_name(dirty_name: str):
    # Sanitize the label. Not for security, but just to hope that
    # any external tools don't freak out about labels they don't like.
    clean_name = ""
    for char in dirty_name.removeprefix("_fragment_").removesuffix("Fragment").removesuffix("fragment"):
        if char == " ":
            char = "_"
        if char.isascii() and (char.isalnum() or char in "_-"):
            clean_name += char
    if not clean_name[0].isalpha():
        clean_name = "L" + clean_name
    return clean_name

class FragmentDataItem(Enum):
    FRAGMENT_NAME = auto()
    COLOR_NAME = auto()

    @classmethod
    def _missing_(cls, value):
        for kind in cls:
            if kind.name.lower() == value.lower():
                return kind

    def __str__(self):
        return self.name.lower()

def _spec_to_fragments(spec: str) -> tuple[list[fragments.Fragment], list[str]]:
    """Convert a single line spec string to a list of renderable fragments."""
    fragment_list = []
    fragment_name_list = []
    for part in RE_FRAGMENT.split(spec):
        if part.startswith("{") and not part.startswith("{{") and part.endswith("}"):
            # We have a special fragment. Find and instantiate it.
            fragment = fragments.fragment_from_spec(part[1:-1])
            fragment_list.append(fragment)
            if isinstance(fragment, fragments.FunctionalFragment):
                fun_frag = fragment.fn
                if isinstance(fun_frag, Callable):
                    fragment_name_list.append(clean_up_name(fun_frag.__name__))
            else:
                fragment_name_list.append(clean_up_name(fragment.__class__.__name__))

        else:
            # We have text. Build123d Text object doesn't handle leading/
            # trailing spaces, so let's split them out here and put in
            # explicit whitespace fragments
            part = part.replace("{{", "{").replace("}}", "}")
            left_spaces = part[: len(part) - len(part.lstrip())]
            if left_spaces:
                fragment_list.append(fragments.WhitespaceFragment(left_spaces))
                fragment_name_list.append(clean_up_name(fragments.WhitespaceFragment.__name__))
            part = part.lstrip()

            part_stripped = part.strip()
            if part_stripped:
                fragment_list.append(fragments.TextFragment(part_stripped))
                fragment_name_list.append(clean_up_name(part_stripped))

            if chars := len(part) - len(part_stripped):
                fragment_list.append(fragments.WhitespaceFragment(part[-chars:]))
                fragment_name_list.append(clean_up_name(fragments.WhitespaceFragment.__name__))
    return fragment_list, fragment_name_list

class LabelRenderer:
    def __init__(self, options: RenderOptions):
        self.opts = options

    def render_batch(self, spec: str, area: Vector) -> Compound:
        """
        Given a specification string, render a single label.

        Args:
            spec: The string representing the label.
            area: The width and height the label should be confined to.

        Returns:
            A rendered Compound object with the label contents, centered on
            the origin.
        """
        # Area splitting
        SPLIT_RE = fragments.SplitterFragment.SPLIT_RE
        columns = []
        column_proportions: list[float] = []

        def _handle_spec_alignment(scoped_spec) -> tuple[str, str | None]:
            """Handle alignment fragment at start of a label."""
            # Special handling: First column alignment is at start of string
            if scoped_spec[:3] in {"{<}", "{>}"}:
                return scoped_spec[3:], scoped_spec[1]
            else:
                return scoped_spec, None

        # spec, first_alignment = _handle_spec_alignment(spec)

        for label, *divider in batched(
            fragments.SplitterFragment.SPLIT_RE.split(spec), SPLIT_RE.groups + 1
        ):
            label, alignment = _handle_spec_alignment(label)

            # The last round of this loop will not have any divider
            if divider:
                split = fragments.SplitterFragment(*divider)
                if not column_proportions:
                    # We're the first divider, define both
                    column_proportions = [split.left, split.right]
                else:
                    # Proportions are relative to the previous column. Left is not
                    # used except to define right in relation to the previous column
                    column_proportions.append(
                        split.right / split.left * column_proportions[-1]
                    )
            # If we've specified an alignment, pre-process to add alignment
            # fragments to every line
            if alignment:
                parts = label.splitlines()
                if label.endswith("\n"):
                    parts.append("")
                new_parts = []
                for part in parts:
                    if not part or "{...}" in part or "{measure}" in part:
                        new_parts.append(part)
                    else:
                        new_parts.append(
                            f"{part}{{...}}" if alignment == "<" else f"{{...}}{part}"
                        )
                label = "\n".join(new_parts)

            columns.append(label)

        if not column_proportions:
            column_proportions = [1]

        # Calculate column widths
        total_proportions = sum(column_proportions)
        column_gaps_width = self.opts.column_gap * (len(columns) - 1)
        column_widths = [
            x * (area.X - column_gaps_width) / total_proportions
            for x in column_proportions
        ]
        logger.debug(f"{column_widths=}")
        logger.debug(f"{column_proportions=}")

        child_pcomps = []
        x = -area.X / 2
        for column_spec, width in zip(columns, column_widths):
            xy = Location(((x + (width / 2), 0)))
            with Locations([xy]):
                  ch_pc = self._do_multiline_render(column_spec, Vector(X=width, Y=area.Y))
                  ch_pc.locate(xy)
                  child_pcomps.append(ch_pc)
            x += width + self.opts.column_gap

        batch_compound = Compound(children=child_pcomps)
        batch_compound.label = clean_up_name(get_global_label("Batch"))
        return batch_compound

    def _do_multiline_render(
        self, spec: str, area: Vector, is_rescaling: bool = False) -> Compound:
        """Label render function, with ability to recurse."""
        lines = spec.splitlines()
        if spec.endswith("\n"):
            lines.append("")

        if not lines:
            raise ValueError("Asked to render empty label")

        row_height = (area.Y - (self.opts.line_spacing_mm * (len(lines) - 1))) / len(lines)

        child_pcomps = []
        # Render each line into the Compound separately
        for n, line in enumerate(lines):
            # Handle blank lines
            if not line:
                continue
            # Calculate the y of the line center
            render_y = (
                area.Y / 2
                - (row_height + self.opts.line_spacing_mm) * n
                - row_height / 2
            )
            logger.info(f'Rendering line {n+1} ("{line}")')
            IndentingRichHandler.indent()
            xy = Location((0, render_y))
            with Locations([xy]):
                ch_pc = self._render_single_line(
                    line,
                    Vector(X=area.X, Y=row_height),
                    allow_overheight=self.opts.allow_overheight,
                )
                ch_pc.label = clean_up_name(get_global_label("Line"))
                ch_pc.locate(xy)
                child_pcomps.append(ch_pc)
            IndentingRichHandler.dedent()

        ml_compound = Compound(children=child_pcomps)
        ml_compound.label = clean_up_name(get_global_label("Multiline"))

        bbox = ml_compound.bounding_box()
        scale_to_maxwidth = area.X / bbox.size.X
        scale_to_maxheight = area.Y / bbox.size.Y

        if scale_to_maxheight < 1 - 1e3:
            print(
                f"Vertical scale is too high for area ({scale_to_maxheight}); downscaling"
            )
        to_scale = min(scale_to_maxheight, scale_to_maxwidth, 1)
        print("Got scale: " + str(to_scale))
        if to_scale < 0.99 and not is_rescaling:
            print(f"Rescaling as {scale_to_maxwidth}")
            # We need to scale this down. Resort to adjusting the height and re-requesting.
            # second = make_text_label(
            #     spec,
            #     maxwidth,
            #     maxheight=maxheight * scale_to_maxwidth * 0.95,
            #     _rescaling=True,
            # )

            # If we had an area that didn't fill the whole height, then we need
            # to scale down THAT height, instead of the "total available" height
            height_to_scale = min(area.Y, bbox.size.Y)

            second_try = self._do_multiline_render(
                spec,
                Vector(X=area.X, Y=height_to_scale * to_scale * 0.95),
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
            print_spec = spec.replace("\n", "\\n")
            print(
                f'Entry "{print_spec}" calculated width = {bbox.size.X:.1f} (max {area.X})'
            )
            return second_try
        print(
            f'Entry "{spec}" calculated width = {bbox.size.X:.1f} (max {area.X})'
        )

        return ml_compound

    def _render_single_line(
        self, line: str, area: Vector, allow_overheight: bool) -> Compound:
        """
        Render a single line of a labelspec.
        """
        # Firstly, split the line into a set of fragment objects
        frags, frag_names = _spec_to_fragments(line)

        # Now pre-process the modifier fragments and record stuff into
        # a dictionary for later use; those modifier fragments are
        # removed from the list of fragments

        # For modifier fragments, the change needs to happen
        # in this loop so that fragment order is preserved.
        # If you need to reference something later, when the
        # Sketch is extruded into a Part (which is pretty
        # likely!), a good technique is to store info as
        # entries in the fragment_data dictionary that gets
        # attached to the Fragment object

        current_color = self.opts.default_color
        renderable_frags = []
        for fragdex, frag in enumerate(frags):
            if isinstance(frag, fragments.ModifierFragment):

                if isinstance(frag, fragments.ColorFragment):
                    logger.info(f"Switching to color '{frag.color}'")
                    current_color = frag.color

            else:
                fragment_data = {}
                fragment_data[FragmentDataItem.COLOR_NAME] = current_color
                fragment_data[FragmentDataItem.FRAGMENT_NAME] = frag_names[fragdex]
                frag.fragment_data = fragment_data
                renderable_frags.append(frag)
        frags = renderable_frags

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

        child_parts = []
        # Assemble these onto the target
        x = -total_width / 2
        for fragment, frag_sketch in [(x, rendered[x]) for x in frags]:
            fragment_width = frag_sketch.bounding_box().size.X
            fxy = Location(((x + fragment_width / 2, 0)))
            with Locations(fxy):
                if fragment.visible:
                    with BuildPart(mode=Mode.PRIVATE) as child_bpart:
                        # EMBOSSED gets raised, DEBOSSED and EMBEDDED get lowered
                        extrude(frag_sketch, self.opts.depth if self.opts.label_style == LabelStyle.EMBOSSED else -self.opts.depth)
                    child_part = child_bpart.part
                    child_part_color_name = fragment.fragment_data[FragmentDataItem.COLOR_NAME]
                    child_part.color = child_part_color_name
                    child_part.locate(fxy)
                    fragment_name = fragment.fragment_data[FragmentDataItem.FRAGMENT_NAME]
                    child_part_label = fragment_name if fragment_name else "item"
                    if child_part_color_name != self.opts.default_color:
                        child_part_label += "__" + child_part_color_name
                    child_part.label = clean_up_name(get_global_label(child_part_label))
                    child_parts.append(child_part)
            x += fragment_width

        sl_compound = Compound(children=child_parts)
        sl_compound.label = clean_up_name(get_global_label("Line"))
        return sl_compound
        
def render_divided_label(
    labels: str, area: Vector, divisions: int, options: RenderOptions) -> Compound:
    """
    Create a Compound for multiple labels fitted into a single area
    """
    area = Vector(X=area.X - options.margin_mm * 2, Y=area.Y - options.margin_mm * 2)
    area_per_label = Vector(area.X / divisions, area.Y)
    leftmost_label_x = -area.X / 2 + area_per_label.X / 2
    renderer = LabelRenderer(options)
    child_pcomps = []
    for i, label in enumerate(labels):
        xy = Location(((leftmost_label_x + i * area_per_label.X, 0)))
        with Locations([xy]):
            if label.strip():
                ch_pc = renderer.render_batch(label, area_per_label)
                ch_pc.locate(xy)
                child_pcomps.append(ch_pc)

    div_compound = Compound(children=child_pcomps)
    div_compound.label = clean_up_name(get_global_label("Batches"))
    return div_compound

def render_collection_of_labels(labels:list(str), divisions:int, y_offset_each_label:float, options:RenderOptions, label_area:Vector) -> Compound:
    child_pcomps = []
    y = 0
    physical_label_count = 0
    batch_iter = batched(labels, divisions)
    for ba in batch_iter:
        labels = ba
        physical_label_count +=1
        xy = Location([0, y])
        with Locations([xy]):
            try:
                ch_pc = render_divided_label(
                        labels,
                        label_area,
                        divisions=divisions,
                        options=options,
                    )
                ch_pc.label = clean_up_name(get_global_label("Label"))  #  a physical label
                ch_pc.locate(xy)
                child_pcomps.append(ch_pc)

            except fragments.InvalidFragmentSpecification as e:
                rich.print(f"\n[y][b]Could not proceed: {e}[/b][/y]\n")
                sys.exit(1)
        y -= y_offset_each_label

    labels_compound = Compound(children=child_pcomps)
    labels_compound.label = clean_up_name("Labels")
    logger.debug(f"FULL   COMPOUND {labels_compound}\n{labels_compound.show_topology()}")
    simplify_the_tree(labels_compound)
    logger.info(f"SIMPLIFIED topology\n{labels_compound.show_topology(limit_class=Part)}")
    return labels_compound

def simplify_the_tree(comp: Compound):
    """Walk the tree of a Compound to eliminate unecessary nodes (those with only a single child)"""
    # Sorry to all the middle managers we're laying off :-)
    # other than Parts, all Compounds here have at least 1 child, which eliminated some
    # cluttery defensive checking
    parent = comp.parent
    single_child_parent = None
    adjustment = Vector(0,0,0)
    while parent and len(parent.children) == 1:
        single_child_parent = parent
        adjustment += parent.location.position
        parent = parent.parent
    if single_child_parent:
        # this relative adjustment is made to account for the locations of
        # the eliminated single-child nodes in the original hierarchy
        comp.move(Location(position=adjustment))
        # promote the hierarchical label upwards, with 2 exceptions:
        # part labels stay where they are, and the very top of the tree is not replaced
        if parent and not isinstance(comp, Part):
            single_child_parent.label = comp.label
        if parent:
            # look for the child with the matching label and replace it with this comp
            new_children = []
            for child in parent.children:
                if child.label == single_child_parent.label:
                    new_children.append(comp)
                else:
                    new_children.append(child)
            parent_location = parent.location
            # Child assignment tweaks Compound location, so restore it
            parent.children = new_children
            parent.location = parent_location
        else:
            parent_location = single_child_parent.location
            single_child_parent.children = [comp]
            single_child_parent.location = parent_location
    # this is the recursion stopping condition (all leafs are Parts)
    if not isinstance(comp, Part):
        for child in comp.children:
            simplify_the_tree(child)
