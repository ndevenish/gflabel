from __future__ import annotations

import functools
import logging
import re
import textwrap
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from math import cos, radians, sin
from typing import Any, Iterable, NamedTuple, Type

from build123d import (
    Align,
    Axis,
    BuildLine,
    BuildSketch,
    CenterArc,
    Circle,
    EllipticalCenterArc,
    GridLocations,
    Line,
    Location,
    Locations,
    Mode,
    Plane,
    PolarLocations,
    Polyline,
    Rectangle,
    RegularPolygon,
    Sketch,
    SlotCenterToCenter,
    Text,
    Triangle,
    Vector,
    add,
    fillet,
    make_face,
    mirror,
    offset,
)

from .options import RenderOptions

logger = logging.getLogger(__name__)
RE_FRAGMENT = re.compile(r"(.+?)(?:\((.*)\))?$")

FRAGMENTS: dict[str, Type[Fragment] | Callable[..., Fragment]] = {}

# Alias names for drive. These should be remapped before rendering
DRIVE_ALIASES = {
    "+": "phillips",
    "posidrive": "pozidrive",
    "posi": "pozidrive",
    "pozi": "pozidrive",
    "-": "slot",
    "tri": "triangle",
}
DRIVES = {
    "phillips",
    "pozidrive",
    "slot",
    "hex",
    "cross",
    "square",
    "triangle",
    "torx",
    "security",
    "phillipsslot",
}


def fragment_from_spec(spec: str) -> Fragment:
    # If the fragment is just a number, this is distance to space out
    try:
        value = float(spec)
    except ValueError:
        pass
    else:
        return SpacerFragment(value)

    # Is a fragment name, optionally with arguments
    match = RE_FRAGMENT.match(spec)
    assert match
    name, args = match.groups()
    args = [x.strip() for x in args.split(",")] if args else []

    if name not in FRAGMENTS:
        raise RuntimeError(f"Unknown fragment class: {name}")
    return FRAGMENTS[name](*args)


def fragment(*names: str, examples: list[str] = [], overheight: float | None = None):
    """Register a label fragment generator"""

    def _wrapped(
        fn: Type[Fragment] | Callable[[float, float], Sketch],
    ) -> Type[Fragment] | Callable[[float, float], Sketch]:
        if not isinstance(fn, type) and callable(fn):
            logger.debug(f"Wrapping fragment function {fn}")

            # We can have callable functions
            # class FnWrapper(Fragment):
            #     def render(
            #         self, height: float, maxsize: float, options: Any
            #     ) -> Sketch:
            #         return orig_fn(height, maxsize)
            def fragment(*args):
                frag = FunctionalFragment(fn, *args)
                frag.overheight = overheight
                frag.examples = examples
                return frag

            # fragment = lambda *args: FunctionalFragment(fn, *args)
            fragment.__doc__ = fn.__doc__
            setattr(fragment, "examples", examples)
            setattr(fragment, "overheight", overheight)
        else:
            fragment = fn
        # Now assign this in the name dict
        for name in names:
            logger.debug(f"Registering fragment {name}")
            FRAGMENTS[name] = fragment
        return fn

    return _wrapped


class Fragment(metaclass=ABCMeta):
    # Is this a fixed or variable-width fragment?
    variable_width = False

    # If variable width, higher priority fragments will be rendered first
    priority: float = 1

    # If this fragment is visible. If not visible, rendered sketch will
    # indicate bounding box only, but should never be added.
    visible = True

    # An example, or list of examples, demonstrating the fragment.
    examples: list[str] | None = None

    # Fragments are allowed to go overheight, in which case the entire
    # label is scaled down to fit. If this is set then the working area
    # will preemptively be scaled to compensate, avoiding a double-round
    # of resizing.
    overheight: float | None = None

    def __init__(self, *args: list[Any]):
        if args:
            raise ValueError("Not all fragment arguments handled")

    # If this fragment is variable, what's the smallest it can go?
    def min_width(self, height: float) -> float:
        """If this fragment is variable, what's the smallest it can go?"""
        if self.variable_width:
            raise NotImplementedError(
                f"min_width not implemented for variable width object '{type(self).__name__}'"
            )
        return 0

    @abstractmethod
    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        pass


class FunctionalFragment(Fragment):
    """Simple fragment for registering uncomplicated fragments"""

    def __init__(self, fn: Callable[[float, float], Sketch], *args):
        self.args = args
        self.fn = fn

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        return self.fn(height, maxsize, *self.args)


class SpacerFragment(Fragment):
    visible = False

    examples = ["L{...}R\n{...}C{...}R"]

    def __init__(self, distance: float, *args):
        super().__init__(*args)
        self.distance = distance

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        with BuildSketch() as sketch:
            Rectangle(self.distance, height)
        return sketch.sketch


@fragment("...")
class ExpandingFragment(Fragment):
    """
    Blank area that always expands to fill available space.

    If specified multiple times, the areas will be balanced between
    entries. This can be used to justify/align text.
    """

    variable_width = True
    priority = 0
    visible = False

    examples = ["L{...}R"]

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        with BuildSketch() as sketch:
            Rectangle(maxsize, height)
        return sketch.sketch

    def min_width(self, height: float) -> float:
        return 0


class TextFragment(Fragment):
    def __init__(self, text: str):
        self.text = text

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        with BuildSketch() as sketch:
            Text(
                self.text,
                font_size=options.font.font_height_mm or height,
                font=options.font.font,
                font_style=options.font.font_style,
            )
        return sketch.sketch


@functools.lru_cache
def _whitespace_width(spacechar: str, height: float, options: RenderOptions) -> float:
    """Calculate the width of a space at a specific text height"""
    w2 = (
        Text(
            f"a{spacechar}a",
            font_size=options.font.font_height_mm or height,
            font=options.font.font,
            font_style=options.font.font_style,
            mode=Mode.PRIVATE,
        )
        .bounding_box()
        .size.X
    )
    wn = (
        Text(
            "aa",
            font_size=options.font.font_height_mm or height,
            font=options.font.font,
            font_style=options.font.font_style,
            mode=Mode.PRIVATE,
        )
        .bounding_box()
        .size.X
    )
    return w2 - wn


class WhitespaceFragment(Fragment):
    visible = False

    def __init__(self, whitespace: str):
        if not whitespace.isspace():
            raise ValueError(
                f"Whitespace fragment can only contain whitespace, got {whitespace!r}"
            )
        self.whitespace = whitespace

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        with BuildSketch() as sketch:
            Rectangle(_whitespace_width(self.whitespace, height, options), height)
        return sketch.sketch


@fragment("hexhead", examples=["{hexhead}"])
def _fragment_hexhead(height: float, _maxsize: float, *drives: str) -> Sketch:
    """Hexagonal screw head. Will accept drives, but not compulsory."""
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        RegularPolygon(height / 2, 6)
        if drives:
            add(
                compound_drive_shape(drives, 0.6 * height / 2, height / 2),
                mode=Mode.SUBTRACT,
            )
    return sketch.sketch


@fragment("head")
def _fragment_head(height: float, _maxsize: float, *headshapes: str) -> Sketch:
    """Screw head with specifiable head-shape."""
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
        # Intersect all of the heads together
        add(
            compound_drive_shape(
                headshapes, radius=(height / 2) * 0.7, outer_radius=height / 2
            ),
            mode=Mode.SUBTRACT,
        )
    return sketch.sketch


@fragment("threaded_insert", examples=["{threaded_insert}"])
def _fragment_insert(height: float, _maxsize: float) -> Sketch:
    """Representation of a threaded insert."""
    with BuildSketch() as sketch:
        with BuildLine() as line:
            Polyline(
                [(-3, 0), (-3, 2.5), (-5, 2.5), (-5, 5), (0, 5)],
            )
            mirror(line.line, Plane.XZ)
            mirror(line.line, Plane.YZ)
            fillet(line.vertices(), radius=0.2)
        make_face()

        def Trap() -> Sketch:
            """Generate the Trapezoid shape"""
            with BuildSketch(mode=Mode.PRIVATE) as sketch:
                with BuildLine() as _line:
                    Polyline(
                        [
                            (-1.074, 0.65),
                            (-0.226, 0.65),
                            (1.074, -0.65),
                            (0.226, -0.65),
                        ],
                        close=True,
                    )
                make_face()
            return sketch.sketch

        with GridLocations(1.625, 7.5, 5, 2):
            trapz = Trap()
            add(trapz, mode=Mode.SUBTRACT)

    scale = height / 10
    return sketch.sketch.scale(scale)


@fragment("hexnut", "nut", examples=["{nut}"])
def _fragment_hexnut(height: float, _maxsize: float) -> Sketch:
    """Hexagonal outer profile nut with circular cutout."""
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        RegularPolygon(height / 2, side_count=6)
        Circle(height / 2 * 0.4, mode=Mode.SUBTRACT)
    return sketch.sketch


@fragment("washer", examples=["{washer}"])
def _fragment_washer(height: float, _maxsize: float) -> Sketch:
    """Circular washer with a circular hole."""
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
        Circle(height / 2 * 0.4, mode=Mode.SUBTRACT)
    return sketch.sketch


class BoltBase(Fragment):
    """Base class for handling common bolt/screw configuration"""

    # The options for head shape
    HEAD_SHAPES = {"countersunk", "pan", "round", "socket"}
    # Other, non-drive features
    MODIFIERS = {"tapping", "flip"}
    # Other names that features can be known as, and what they map to
    FEATURE_ALIAS = {
        "countersink": "countersunk",
        "tap": "tapping",
        "tapped": "tapping",
        "flipped": "flip",
    }
    DEFAULT_HEADSHAPE = "pan"

    def __init__(self, *req_features: str):
        # Lower case, remap names, convert to set
        features = {self.FEATURE_ALIAS.get(x.lower(), x.lower()) for x in req_features}

        requested_head_shapes = features & self.HEAD_SHAPES
        if len(requested_head_shapes) > 1:
            raise ValueError("More than one head shape specified")
        self.headshape = next(iter(requested_head_shapes), self.DEFAULT_HEADSHAPE)
        features -= {self.headshape}

        # A list of all modifier options that aren't drives
        self.modifiers = features & self.MODIFIERS
        features -= self.MODIFIERS

        # Drives is everything left
        self.drives = features


@fragment("bolt")
class BoltFragment(BoltBase):
    """
    Variable length bolt, in the style of Printables pred-box labels.

    If the requested bolt is longer than the available space, then the
    bolt will be as large as possible with a broken thread.
    """

    variable_width = True

    def __init__(self, length: str, *features: str):
        self.slotted = bool({"slotted", "slot"} & {x.lower() for x in features})
        self.flanged = bool({"flanged", "flange"} & {x.lower() for x in features})
        features = tuple(x for x in features if x.lower() not in {"slotted", "flanged"})

        self.length = float(length)
        super().__init__(*features)

    def min_width(self, height: float) -> float:
        return height

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        length = self.length
        # line width: How thick the head and body are
        lw = height / 2.25
        # The half-width of the dividing split
        half_split = 0.75

        # Don't allow lengths smaller than lw
        # length = max(length, lw * 2 + half_split)
        maxsize = max(maxsize, lw * 2 + half_split * 2 + 0.1)
        # Work out what the total length is, and if this is over max size
        # then we need to cut the bolt
        split_bolt = length + lw > maxsize
        # Halfwidth distance
        if split_bolt:
            hw = maxsize / 2
        else:
            hw = (length + lw) / 2

        head_h = height / 2
        # If asked for flanged, just shrink the head vertically
        if self.flanged:
            head_h -= lw / 3

        # Work out what the bottom of the bolt looks like
        if "tapping" in self.modifiers:
            bolt_bottom = [(hw - lw / 2, lw / 2), (hw, 0), (hw - lw / 2, -lw / 2)]
        else:
            bolt_bottom = [(hw, lw / 2), (hw, -lw / 2)]

        # Whether the bolt is split or not, we always need a head part
        with BuildSketch(mode=Mode.PRIVATE) as sketch:
            with BuildLine() as _line:
                # Draw the head of the bolt
                # These head connectors are the anchor points for the rest
                head_connector_top: Vector
                head_connector_bottom: Vector
                if self.headshape == "pan":
                    head_radius = min(2, lw / 2)
                    _top_arc = CenterArc(
                        (-hw + head_radius, head_h - head_radius),
                        head_radius,
                        90,
                        90,
                    )
                    _bottom_arc = CenterArc(
                        (-hw + head_radius, -head_h + head_radius),
                        head_radius,
                        180,
                        90,
                    )
                    Line([_top_arc @ 1, _bottom_arc @ 0])
                    if head_radius == lw:
                        head_connector_top = _top_arc @ 0
                        head_connector_bottom = _bottom_arc @ 1
                    else:
                        head_connector_top = Vector(-hw + lw, head_h)
                        head_connector_bottom = Vector(-hw + lw, -head_h)
                        Line([head_connector_top, _top_arc @ 0])
                        Line([head_connector_bottom, _bottom_arc @ 1])
                elif self.headshape == "socket":
                    _head = Polyline(
                        [
                            (-hw + lw, -head_h),
                            (-hw, -head_h),
                            (-hw, head_h),
                            (-hw + lw, head_h),
                        ]
                    )
                    head_connector_bottom = _head @ 0
                    head_connector_top = _head @ 1
                elif self.headshape == "countersunk":
                    head_connector_bottom = Vector(-hw, -head_h)
                    head_connector_top = Vector(-hw, head_h)
                    Line([head_connector_bottom, head_connector_top])
                elif self.headshape == "round":
                    _head = EllipticalCenterArc((-hw + lw, 0), lw, head_h, 90, -90)
                    head_connector_top = _head @ 0
                    head_connector_bottom = _head @ 1
                else:
                    raise ValueError(f"Unknown bolt head type: {self.headshape!r}")

                if not split_bolt:
                    # This line continuously covers the whole bolt
                    Polyline(
                        [
                            head_connector_top,
                            (-hw + lw, lw / 2),
                            *bolt_bottom,
                            (-hw + lw, -lw / 2),
                            head_connector_bottom,
                        ],
                    )
                else:
                    # We have the divider attached to the head to make
                    x_shaft_midpoint = lw + (maxsize - lw) / 2 - hw
                    Polyline(
                        [
                            head_connector_top,
                            (-hw + lw, lw / 2),
                            # Divider is halfway along the shaft
                            (x_shaft_midpoint + lw / 2 - half_split, lw / 2),
                            (x_shaft_midpoint - lw / 2 - half_split, -lw / 2),
                            (-hw + lw, -lw / 2),
                            head_connector_bottom,
                        ],
                    )

            make_face()

            # If we've a split bolt, then we have a second face to make
            if split_bolt:
                with BuildLine() as _line:
                    Polyline(
                        [
                            # Divider is halfway along the shaft
                            (x_shaft_midpoint + lw / 2 + half_split, lw / 2),
                            *bolt_bottom,
                            (x_shaft_midpoint - lw / 2 + half_split, -lw / 2),
                        ],
                        close=True,
                    )
                make_face()

            if self.slotted:
                with Locations([(-hw, 0)]):
                    Rectangle(
                        lw / 2,
                        lw / 2,
                        align=(Align.MIN, Align.CENTER),
                        mode=Mode.SUBTRACT,
                    )
            if self.flanged:
                with Locations([(-hw + lw, 0)]):
                    Rectangle(lw / 4, height, align=(Align.MAX, Align.CENTER))

        if "flip" in self.modifiers:
            return sketch.sketch.scale(-1)

        return sketch.sketch


@fragment("webbolt")
class WebbBoltFragment(BoltBase):
    """
    Alternate bolt representation incorporating screw drive, with fixed length.
    """

    overheight = 1.6

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        height *= self.overheight
        # 12 mm high for 15 mm wide. Scale to this.
        width = 15 / 12 * height
        # Relative proportion of body:head
        body_w = width / 2
        # How many threads to have on the body
        n_threads = 6
        # How deep each thread profile should be
        thread_depth = 0.5

        # Calculated values
        head_w = width - body_w
        x_head = body_w - width / 2

        x0 = -width / 2

        thread_pitch = body_w / n_threads
        thread_lines: list[tuple[float, float]] = [(x0, 0)]
        thread_tip_height = height / 4 + thread_depth

        if "tapping" in self.modifiers:
            thread_lines.append(
                (x0 + thread_pitch * 2 - 0.2, thread_tip_height - thread_depth)
            )
            n_threads -= 2
            # Just shift the X origin. Not neat, but works.
            x0 += thread_pitch * 2

        # Make a zig-zag for the bolt head.
        # Only the zig is added, the zag is implicit by connecting to
        # another zig immediately (or the explicit end-of-zag of the head)
        for i in range(n_threads):
            thread_lines.extend(
                [
                    (x0 + i * thread_pitch, thread_tip_height - thread_depth),
                    (x0 + (i + 0.5) * thread_pitch, thread_tip_height),
                ]
            )

        with BuildSketch() as sketch:
            with BuildLine() as line:
                # The point that the thread connects to the head
                head_connector: Vector
                if self.headshape == "pan":
                    head_radius = 2
                    head_arc = CenterArc(
                        (width / 2 - head_radius, height / 2 - head_radius),
                        head_radius,
                        0,
                        90,
                    )
                    Line([head_arc @ 0, (width / 2, 0)])
                    _top = Line([(x_head, height / 2), head_arc @ 1])
                    head_connector = _top @ 0
                elif self.headshape == "countersunk":
                    _top = Line([(width / 2, height / 2), (width / 2, 0)])
                    head_connector = _top @ 0
                elif self.headshape == "socket":
                    head_connector = (
                        Polyline(
                            [
                                (x_head, height / 2),
                                (width / 2, height / 2),
                                (width / 2, 0),
                            ]
                        )
                        @ 0
                    )
                elif self.headshape == "round":
                    # Two cases:
                    # - head wider than height/2, circular head and flat
                    # - head smaller than height/2, squashed head
                    if head_w > height / 2:
                        x_roundhead = width / 2 - height / 2
                        _arc = CenterArc((x_roundhead, 0), height / 2, 0, 90)
                        flat = Line(
                            [
                                (x_head, height / 2),
                                _arc @ 1,
                            ]
                        )
                        head_connector = flat @ 0
                    else:
                        # But! Geometry means we will never get latter, at
                        # least for now. So guard against it.
                        raise NotImplementedError(
                            "Round head on this aspect is not implemented. This should never happen."
                        )

                Polyline(
                    [
                        *thread_lines,
                        (x_head, thread_tip_height - thread_depth),
                        head_connector,
                    ]
                )

                mirror(line.line, Plane.XZ)
            make_face()

            if self.drives:
                # thread_depth/2 is just a "fudge" to slightly off-center it
                fudge = thread_depth / 2
                location = Location((width / 2 - head_w / 2 - fudge, 0))
                add(
                    compound_drive_shape(
                        self.drives,
                        radius=head_w * 0.9 / 2,
                        outer_radius=head_w / 2,
                    ).locate(location),
                    mode=Mode.SUBTRACT,
                )

        if "flip" in self.modifiers:
            return sketch.sketch.scale(-1)

        return sketch.sketch


@fragment("variable_resistor", examples=["{variable_resistor}"], overheight=1.5)
def _fragment_variable_resistor(height: float, maxsize: float) -> Sketch:
    """Electrical symbol of a variable resistor."""
    t = 0.4 / 2  # Line half-thickness. Lines are offset by this.
    w = 6.5  # Width of resistor
    h = 2  # Height of resistor
    l_arr = 7  # Arrow length
    l_head = 1.5  # Arrow head length
    angle = 30  # Angle of Arrow

    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        with BuildLine():
            Polyline(
                [
                    (-6, 0),
                    (-6, t),
                    (-w / 2 - t, t),
                    (-w / 2 - t, h / 2 + t),
                    (0, h / 2 + t),
                    (0, h / 2 - t),
                    (-w / 2 + t, h / 2 - t),
                    (-w / 2 + t, 0),
                ],
                close=True,
            )
        make_face()
        mirror(sketch.sketch, Plane.XZ)
        mirror(sketch.sketch, Plane.YZ)

        theta = radians(angle)
        with BuildSketch(mode=Mode.PRIVATE) as arrow:
            with BuildLine() as _line:
                Polyline(
                    [
                        (0, -l_arr / 2),
                        (0, l_arr / 2),
                        (-sin(theta) * l_head, l_arr / 2 - cos(theta) * l_head),
                    ]
                )
                offset(amount=t)
            make_face()
            mirror(arrow.sketch, Plane.YZ)
        add(arrow.sketch.rotate(Axis.Z, -30))

    # Scale to fit in our height
    size = sketch.sketch.bounding_box().size
    scale = (height * 1.5) / size.Y

    return sketch.sketch.scale(scale)


def drive_shape(shape: str, radius: float = 1, outer_radius: float = 1) -> Sketch:
    """
    Returns a shape representing a particular screw head.

    Args:
        shape: Name of the shape to generate.
        radius: Radius to draw head to.
        outer_radius:
            Width to extend head shape if it cuts the whole head. e.g.
            this is the width of the head circle to cut the edges.
    """
    positive = False
    shape = shape.lower()
    cut_radius = max(radius, outer_radius) / radius
    with BuildSketch(mode=Mode.PRIVATE) as sk:
        if shape in {"phillips", "+"}:
            # Phillips head
            Rectangle(1, 0.2)
            Rectangle(0.2, 1)
            Rectangle(0.4, 0.4, rotation=45)
        elif shape in {"pozidrive", "posidrive", "posi", "pozi"}:
            # Pozidrive
            Rectangle(1, 0.2)
            Rectangle(0.2, 1)
            Rectangle(0.4, 0.4, rotation=45)
            Rectangle(1, 0.1, rotation=45)
            Rectangle(1, 0.1, rotation=-45)
        elif shape in {"slot", "-"}:
            Rectangle(cut_radius, 0.2)
        elif shape == "hex":
            RegularPolygon(0.5, side_count=6)
        elif shape == "cross":
            Rectangle(1, 0.2)
            Rectangle(0.2, 1)
        elif shape == "phillipsslot":
            # Phillips head
            Rectangle(1, 0.2)
            Rectangle(0.2, 1)
            Rectangle(0.4, 0.4, rotation=45)
            # And a larger slot
            Rectangle(cut_radius, 0.2)
        elif shape == "square":
            Rectangle(0.6, 0.6, rotation=45)
        elif shape in {"triangle", "tri"}:
            Triangle(a=0.95, b=0.95, c=0.95)
        elif shape == "torx":
            Circle(0.74 / 2)
            with PolarLocations(0, 3):
                SlotCenterToCenter(0.82, 0.19)
            with PolarLocations(0.41, 6, start_angle=360 / 12):
                Circle(0.11, mode=Mode.SUBTRACT)
        elif shape == "security":
            Circle(0.1)
            positive = True
        else:
            raise ValueError(f"Unknown head type: {shape}")

    sketch = sk.sketch.scale(2 * radius)
    sketch.positive = positive
    return sketch


def compound_drive_shape(
    shapes: Iterable[str], radius: float = 1, outer_radius: float = 1
) -> Sketch:
    """Combine several head shapes into one"""
    if not shapes:
        raise ValueError("Have not requested any drive shapes")
    plus: list[Sketch] = []
    minus: list[Sketch] = []
    for shape in shapes:
        sketch = drive_shape(shape, radius=radius, outer_radius=outer_radius)
        (minus if sketch.positive else plus).append(sketch)

    with BuildSketch() as sketch:
        for shape in plus:
            add(shape)
        for shape in minus:
            add(shape, mode=Mode.SUBTRACT)
    return sketch.sketch


@fragment("box", examples=["{box(35)}"])
def _box_fragment(
    height: float, maxsize: float, in_width: str, in_height: str | None = None
) -> Sketch:
    """Arbitrary width, height centered box. If height is not specified, will expand to row height."""
    width = float(in_width)
    height = float(in_height) if in_height else height
    with BuildSketch() as sketch:
        Rectangle(width, height)
    return sketch.sketch


# class FragmentExampleSettings(NamedTuple):
#     base: str
#     width: float
#     height: float | None
#     divisions : int


class FragmentDescriptionRow(NamedTuple):
    names: list[str]
    description: str | None
    examples: list[str]
    # example_style : FragmentExampleSettings


def fragment_description_table() -> list[FragmentDescriptionRow]:
    """
    Generate a collection of information about fragments

    This can be used to e.g. generate fragment help, automatic
    documentation etc.
    """
    descriptions: list[FragmentDescriptionRow] = []
    known_as: dict[Fragment | Callable[..., Fragment], list[str]] = {}
    # Invert the list of fragments, so that we have a list of names for each
    for name, frag in FRAGMENTS.items():
        known_as.setdefault(frag, []).append(name)
    # Now handle each fragment separately
    for fragment, names in known_as.items():
        descriptions.append(
            FragmentDescriptionRow(
                names=sorted(names),
                description=(
                    textwrap.dedent(fragment.__doc__).strip()
                    if fragment.__doc__
                    else None
                ),
                examples=getattr(fragment, "examples", None) or [],
            )
        )
    descriptions.append(
        FragmentDescriptionRow(
            names=["<number>"],
            description="A gap of specific width, in mm.",
            examples=["]{12.5}["],
        )
    )
    return sorted(descriptions, key=lambda x: x.names[0])


if __name__ == "__main__":
    # Generate a markdown table of fragment definitions
    frags = fragment_description_table()
    maxname = max(len(", ".join(frag.names)) for frag in frags)

    # os.geten
    desc_len = 82 - maxname
    print(f"| {'Names':{maxname}} | {'Description':{desc_len}} |")
    print("|" + "-" * (maxname + 2) + "|" + "-" * (desc_len + 2) + "|")

    for frag in frags:

        def _clean(s):
            return s.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        desc = _clean(frag.description)
        names = _clean(", ".join(frag.names))
        print(f"| {names:{maxname}} | {desc:{desc_len}} |")
