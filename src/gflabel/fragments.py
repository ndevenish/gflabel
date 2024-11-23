from __future__ import annotations

import functools
import importlib.resources
import io
import itertools
import json
import logging
import re
import textwrap
import zipfile
from abc import ABCMeta, abstractmethod
from collections.abc import Callable
from math import cos, radians, sin
from typing import Any, ClassVar, Iterable, NamedTuple, Type, TypedDict

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
    Rot,
    Sketch,
    SlotCenterToCenter,
    Text,
    Triangle,
    Vector,
    add,
    fillet,
    import_svg,
    make_face,
    mirror,
    offset,
)

from .options import RenderOptions
from .util import format_table

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


class InvalidFragmentSpecification(RuntimeError):
    pass


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
            with options.font.font_options() as f:
                print(f"Using {f}")
                Text(self.text, font_size=options.font.get_allowed_height(height), **f)
        return sketch.sketch


@functools.lru_cache
def _whitespace_width(spacechar: str, height: float, options: RenderOptions) -> float:
    """Calculate the width of a space at a specific text height"""
    with options.font.font_options() as f:
        w2 = (
            Text(
                f"a{spacechar}a",
                font_size=options.font.get_allowed_height(height),
                mode=Mode.PRIVATE,
                **f,
            )
            .bounding_box()
            .size.X
        )
        wn = (
            Text(
                "aa",
                font_size=options.font.get_allowed_height(height),
                mode=Mode.PRIVATE,
                **f,
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
        inner_radius = 0.55
        Circle(height / 2)
        Circle(height / 2 * inner_radius, mode=Mode.SUBTRACT)
    return sketch.sketch


@fragment("lockwasher", examples=["{lockwasher}"])
def _fragment_lockwasher(height: float, _maxsize: float) -> Sketch:
    """Circular washer with a locking cutout."""
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        inner_radius = 0.55
        Circle(height / 2)
        Circle(height / 2 * inner_radius, mode=Mode.SUBTRACT)
        y_cutout = height / 2 * (inner_radius + 1) / 2
        r = Rectangle(height / 2 * inner_radius / 2, y_cutout * 2, mode=Mode.PRIVATE)
        add(
            r.locate(Location((height * 0.1, y_cutout))).rotate(Axis.Z, 45),
            mode=Mode.SUBTRACT,
        )

    return sketch.sketch

@fragment("circle", examples=["{circle}"])
def _fragment_circle(height: float, _maxsize: float) -> Sketch:
    """A filled circle."""
    with BuildSketch(mode=Mode.PRIVATE) as sketch:
        Circle(height / 2)
    return sketch.sketch


class BoltBase(Fragment):
    """Base class for handling common bolt/screw configuration"""

    # The options for head shape
    HEAD_SHAPES = {"countersunk", "pan", "round", "socket"}
    # Other, non-drive features
    MODIFIERS = {"tapping", "flip", "partial"}
    # Other names that features can be known as, and what they map to
    FEATURE_ALIAS = {
        "countersink": "countersunk",
        "tap": "tapping",
        "tapped": "tapping",
        "flipped": "flip",
        "square": "socket",
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
        self.partial = "partial" in self.modifiers
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
        width = 1.456 * height  # 15 / 12 * height
        # Relative proportion of body:head
        body_w = 0.856 * height  # width / 2
        # How many threads to have on the body
        n_threads = 6
        # How deep each thread profile should be
        thread_depth = 0.0707 * height

        # Calculated values
        head_w = width - body_w
        x_head = body_w - width / 2

        x0 = -width / 2

        thread_pitch = body_w / n_threads
        thread_lines: list[tuple[float, float]] = [(x0, 0)]
        thread_tip_height = (height / 4) + thread_depth

        if "tapping" in self.modifiers:
            thread_lines.append(
                (x0 + thread_pitch * 2 - 0.2, thread_tip_height - thread_depth)
            )
            n_threads -= 2
            # Just shift the X origin. Not neat, but works.
            x0 += thread_pitch * 2

        if self.partial:
            n_threads = 3
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
        if self.partial:
            thread_lines.append(
                (x0 + n_threads * thread_pitch, thread_tip_height - thread_depth)
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


class FragmentDescriptionRow(NamedTuple):
    names: list[str]
    description: str | None
    examples: list[str]


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
            names=["1", "4.2", "..."],
            description="A gap of specific width, in mm.",
            examples=["]{12.5}["],
        )
    )
    return sorted(descriptions, key=lambda x: x.names[0])


class ManifestItem(TypedDict):
    id: str
    name: str
    category: str
    standard: str
    filename: str


@functools.cache
def electronic_symbols_manifest() -> list[ManifestItem]:
    with importlib.resources.files("gflabel").joinpath("resources").joinpath(
        "chris-pikul-symbols.zip"
    ).open("rb") as f:
        zip = zipfile.ZipFile(f)
        return json.loads(zip.read("manifest.json"))


def _get_standard_requested(selectors: Iterable[str]) -> str | None:
    """Given a list of selectors, did we ask for a standard?"""
    aliases = {
        "com": "common",
        "ansi": "ieee",
        "euro": "iec",
        "europe": "iec",
    }
    # Convert this to a set and resolve aliases
    requested = set(aliases.get(x.lower(), x.lower()) for x in selectors)
    # Work out if a specific standard was requested
    standards = {x.upper() for x in requested & {"iec", "ieee", "common"}}
    if len(standards) > 1:
        raise ValueError(
            f"Got more than one symbol standard selected: '{', '.join(standards)}'"
        )
    return next(iter(standards), None)


def _match_electronic_symbol_from_standard(
    preferred_standards: list[str],
    matches: list[ManifestItem],
) -> list[ManifestItem]:
    # IF all matches are in the same category, then choose based on standard.
    def _get_standard(x):
        return x["standard"].lower()

    grouped_match = itertools.groupby(
        sorted(matches, key=lambda x: preferred_standards.index(_get_standard(x))),
        key=_get_standard,
    )
    return list(next(iter(grouped_match), [[]])[1])


def _match_electronic_symbol_with_selectors(selectors: Iterable[str]) -> ManifestItem:
    """
    Match a symbol in the electronics manifest.

    Returns:
        The manifest entry. If no result, a ValueError will be raised.
    """
    # Convert this to a set and resolve aliases
    aliases: dict[str, str] = {}
    requested = set(
        aliases.get(x.lower(), x.lower())
        .removesuffix(".svg")
        .removesuffix(".png")
        .removesuffix(".jpg")
        for x in selectors
    )

    # Work out if we requested a standard
    standard_req = _get_standard_requested(requested)
    # Make a standard order to discriminate otherwise matches
    standards_order = ["common", "iec", "ieee"]
    if standard_req:
        standards_order.remove(standard_req.lower())
        standards_order.insert(0, standard_req.lower())
        requested.remove(standard_req.lower())

    manifest = electronic_symbols_manifest()

    # Firstly, have we been given an exact ID, name or filename
    matches = [
        x
        for x in manifest
        if {
            x["name"].lower(),
            x["id"].lower(),
            x["filename"].lower(),
            # We handle standard separately, but accept exact name
            # with/without it - some of the source components have it
            x["name"]
            .lower()
            .replace(" (IEEE/ANSI)", "")
            .replace(" (Common Style)", ""),
        }
        & requested
    ]
    if len(matches) == 1:
        logger.debug("Found exact electronic symbol match: %s", repr(matches[0]["id"]))
        return matches[0]

    if not matches:
        # We don't have any exact matches, so do fuzzy matching instead
        logger.debug("No exact matches, using fuzzy matches instead")
        # Split the request into a pool of matching tokens
        match_tokens = set(itertools.chain(*[x.split() for x in requested]))
        logger.debug(f"Using match soup: {match_tokens!r}")
        for symbol in manifest:
            # Create a soup for this symbol
            soup = set(
                itertools.chain(
                    *[
                        x.lower().split()
                        for x in {symbol["category"], symbol["name"], symbol["id"]}
                    ]
                )
            )
            if "logic" in soup:
                soup.add("gate")
            # Use this symbol if all of our tokens are in any of the soup
            if all(any(cand in s for s in soup) for cand in match_tokens):
                logger.debug(f"    {symbol['id']} was a complete match!")
                matches.append(symbol)

    if len(matches) == 1:
        logger.debug("Found fuzzy symbol match: %s", repr(matches[0]["id"]))
        return matches[0]

    if not matches:
        raise InvalidFragmentSpecification(
            f"Could find no matches for definition '{','.join(requested)}'"
        )

    # We have multiple matches. Try
    logger.debug(f"Got {len(matches)} matches. Attempting to refine.")

    if len({x["category"] for x in matches}) == 1:
        matches = _match_electronic_symbol_from_standard(standards_order, matches)
        if len(matches) == 1:
            logger.debug(
                f"Using symbol \"{matches[0]['id']}\" because standard [b]{matches[0]['standard']}[/b] is preferred.",
                extra={"markup": True},
            )
            return matches[0]
        else:
            logger.debug(
                f"Preferred standard was not enough to discriminate, {len(matches)} equivalent matches"
            )
    if matches:
        cols = ["ID", "Category", "Name", "Standard", "Filename"]
        logger.error(
            f"Could not decide on symbol from fuzzy specification \"{','.join(requested)}\". Possible options:"
            + "\n"
            + "\n".join(
                format_table(cols, matches, lambda x: x.lower(), prefix="    ")
            ),  # type: ignore
            extra={"markup": "True"},
        )
    else:
        logger.error(
            f"No electronic symbols matched the specification \"{','.join(requested)}\""
        )
    raise InvalidFragmentSpecification("Please specify symbol more precisely.")


@fragment("symbol", "sym")
class _electrical_symbol_fragment(Fragment):
    """Render an electronic symbol."""

    def __init__(self, *selectors: str):
        self.symbol = _match_electronic_symbol_with_selectors(selectors)

        with importlib.resources.files("gflabel").joinpath(
            "resources/chris-pikul-symbols.zip"
        ).open("rb") as f:
            zip = zipfile.ZipFile(f)
            svg_data = io.StringIO(
                zip.read("SVG/" + self.symbol["filename"] + ".svg").decode()
            )
            self.shapes = import_svg(svg_data, flip_y=False)

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        with BuildSketch() as _sketch:
            add(self.shapes)
        bb = _sketch.sketch.bounding_box()
        # Resize this to match the requested height, and to be centered
        return _sketch.sketch.translate(-bb.center()).scale(height / bb.size.Y)


@fragment("|")
class SplitterFragment(Fragment):
    """Denotes a column edge, where the label should be split. You can specify relative proportions for the columns, as well as specifying the column alignment."""

    _SIIF = r"(\d*(?:\d[.]|[.]\d)?\d*)"  # Parses a simple int or float
    SPLIT_RE: ClassVar[re.Pattern] = re.compile(f"\\{{{_SIIF}\\|{_SIIF}}}")

    alignment: str | None

    def __init__(
        self,
        left: str | None = None,
        right: str | None = None,
        *args: list[Any],
    ):
        assert not args
        self.left = float(left or 1)
        self.right = float(right or 1)

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        # This should never happen; for now. We might decide to add
        # options for rendered dividers later.
        raise NotImplementedError("Splitters should never be rendered")


@fragment("measure")
class DimensionFragment(Fragment):
    """
    Fills as much area as possible with a dimension line, and shows the length. Useful for debugging.
    """

    variable_width = True

    examples = ["{measure}A{measure}", "{bolt(10)}{measure}"]

    def min_width(self, height: float) -> float:
        return 1

    def render(self, height: float, maxsize: float, options: RenderOptions) -> Sketch:
        lw = 0.4
        with BuildSketch() as sketch:
            with Locations([(-maxsize / 2, 0)]):
                Rectangle(lw, height / 4, align=(Align.MIN, Align.CENTER))
            with Locations([(maxsize / 2, 0)]):
                Rectangle(lw, height / 4, align=(Align.MAX, Align.CENTER))
            with Locations([(0, 0)]):
                Rectangle(maxsize - lw * 2, lw)

            avail = height / 2 - lw / 2
            with Locations([(0, -avail / 2)]):
                Text(f"{maxsize:.1f}", font_size=height / 2)
        return sketch.sketch


@fragment("<", ">")
class AlignmentFragment(Fragment):
    """Only used at the start of a single label or column. Specifies that all lines in the area should be left or right aligned. Invalid when specified elsewhere."""

    examples = ["{<}Left\nLines", "{>}Right"]

    def __init__(self, *args):
        raise InvalidFragmentSpecification(
            "Got Alignment fragment ({<} or {>}) not at the start of a label; for selective alignment please pad with {...}, or specify alignment in column division."
        )


@fragment("magnet", examples=["{magnet}"])
def _fragment_magnet(height: float, _maxsize: float) -> Sketch:
    """Horseshoe shaped magnet symbol."""
    scale = height * 2 / 3
    thickness = 0.2
    arm_len = 1.8
    with BuildSketch() as sketch:
        Circle(scale / 2)
        Circle(scale / 2 * (1 - thickness * 2), mode=Mode.SUBTRACT)
        Rectangle(
            scale * arm_len, scale, align=(Align.MIN, Align.CENTER), mode=Mode.SUBTRACT
        )
        with Locations(
            (0, scale / 2 - scale * thickness / 2),
            (0, -(scale / 2 - scale * thickness / 2)),
        ):
            Rectangle(scale / 2, scale * thickness, align=(Align.MIN, Align.CENTER))

    return Rot(0, 0, 45) * sketch.sketch


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
            if s is None:
                return ""
            return (
                s.replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
                .replace("|", "\\|")
            )

        if frag.names == ["|"]:
            frag = frag._replace(names=["`|` (pipe)"])
        desc = _clean(frag.description)
        names = _clean(", ".join(frag.names))
        print(f"| {names:{maxname}} | {desc:{desc_len}} |")
