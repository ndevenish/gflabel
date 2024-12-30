from __future__ import annotations

import sys

from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Edge,
    Mode,
    Plane,
    Polyline,
    RectangleRounded,
    Select,
    ShapeList,
    Vector,
    chamfer,
    extrude,
    fillet,
    make_face,
)

from . import LabelBase


def body_v11() -> LabelBase:
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
                with BuildLine() as _line:
                    Polyline(
                        [
                            (x - 0.5, -1),
                            (x - 0.5, -0.8),
                            (x - 1, -0.8),
                            (x - 1, -0.4),
                            (x + 1, -0.4),
                            (x + 1, -0.8),
                            (x + 0.5, -0.8),
                            (x + 0.5, -1),
                        ],
                        close=True,
                    )
                    # mirror(_line.line, Plane.YZ)
                make_face()
        extrude(amount=height / 2, both=True, mode=Mode.SUBTRACT)

        # Now, handle v1.1.0 fillets/chamfers
        verts = (
            part.edges()
            .filter_by(Axis.Z)
            .filter_by(lambda x: x.length < 1)
            .group_by(lambda x: x.length)
        )
        # This needs to be done in two passes in build123d, for some reason
        fillet(verts[0], radius=0.5)
        fillet(verts[1], radius=0.5)

        # Now, find the edges to chamber

        def _get_all_start_edges():
            """Extracts the two Y-axis inner lines for each channel"""
            # Get a list of all edges we want to consider
            all_candidates = (
                part.edges().filter_by(Axis.Y).filter_by_position(Axis.Z, -0.85, -0.75)
            )
            # Now let's select the inner Y-axis edges that we know we want
            start_edges = ShapeList()
            for x in [-12.133, 0, 12.133]:
                start_edges.extend(
                    all_candidates.filter_by_position(Axis.X, x - 0.55, x + 0.55)
                )
            return start_edges

        # Now we follow each of these edges
        def _edge_matcher(vertex_set: ShapeList):
            """Given a list of vertices, returns a matcher for edges touching them"""
            vs = vertex_set.vertices()

            def _match_edge(edge: Edge) -> bool:
                for v in edge.vertices():
                    for v2 in vs:
                        if v.distance_to(v2) < 0.001:
                            return True
                return False

            return _match_edge

        cands_to_chamfer = (
            part.edges().filter_by(Plane.XY).filter_by_position(Axis.Z, -0.85, -0.75)
        )
        # Now, expand the selection twice, following all edges touching the known good edges
        ext_1 = cands_to_chamfer.filter_by(_edge_matcher(_get_all_start_edges()))
        ext_2 = cands_to_chamfer.filter_by(_edge_matcher(ext_1))

        # Finally, Chamfer these. We want 0.2/0.1 but 100% chamfers seem not to work well.
        chamfer(ext_2, length=0.1999, length2=0.1)

    return LabelBase(part.part, Vector(36.4, 11))


def body_v200(width_u: int) -> LabelBase:
    width = 42 * width_u - 6
    height = 11
    depth = 1.2
    with BuildPart() as part:
        # Label body
        with BuildSketch():
            RectangleRounded(width=width, height=height, radius=0.5)
        extrude(amount=-depth)

        # Label edge inset
        with BuildSketch(Plane.XY.offset(-0.4)):
            RectangleRounded(width=width, height=height, radius=0.5)
            RectangleRounded(
                width=width - 0.4, height=height - 0.4, radius=0.3, mode=Mode.SUBTRACT
            )
        extrude(amount=-(depth - 0.6), mode=Mode.SUBTRACT)

        # v1 Cuttings, but only for width = 1 labels
        if width_u == 1:
            with BuildSketch(Plane.XZ) as _sketch:
                for x in [-12.133, 0, 12.133]:
                    with BuildLine() as _line:
                        Polyline(
                            [
                                (x - 0.5, -depth),
                                (x - 0.5, -depth + 0.2),
                                (x - 1, -depth + 0.2),
                                (x - 1, -depth + 0.8),
                                (x + 1, -depth + 0.8),
                                (x + 1, -depth + 0.2),
                                (x + 0.5, -depth + 0.2),
                                (x + 0.5, -depth),
                            ],
                            close=True,
                        )
                        # mirror(_line.line, Plane.YZ)
                    make_face()
            extrude(amount=height / 2, both=True, mode=Mode.SUBTRACT)
            # Fillet the edges of these
            edges = part.edges(Select.LAST).filter_by(Axis.Z)
            fillet(edges, radius=0.5)

    return LabelBase(part.part, Vector(36.4, 11))


def body(version: str = "latest", width: int | None = None) -> LabelBase:
    """
    Generate a Webb-style label body

    Origin is positioned at the center of the label, with the label
    surface at z=0.

    Returns:
        A LabelBase tuple consisting of:
            part: The actual label body.
            label_area: A vector describing the width, height of the usable area.
    """
    known_versions = {"latest", "v1.1", "v2.0.0"}
    if version == "latest":
        version = "v2.0.0"
    if version not in known_versions:
        sys.exit(
            f"Error: Unknown cullenect version: {version}. Valid options: {', '.join(known_versions)}"
        )

    if version == "v1.1":
        if width not in {None, 1}:
            sys.exit(
                f"Error: Gave unexpected width ({width}) for v1.1 cullenect. This version only accepts width 1 labels."
            )

        assert width is None or width == 1
        return body_v11()
    elif version == "v2.0.0":
        return body_v200(width or 1)

    raise RuntimeError(
        "Error: Got to end of cullenect generation without choosing a body!"
    )
