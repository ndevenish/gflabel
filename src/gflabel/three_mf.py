from __future__ import annotations

import lib3mf
from build123d import Color, Part


def _color_to_hex(color: Color | str | None) -> str:
    if color is None:
        return "#808080"
    if isinstance(color, str):
        color = Color(color)

    rgb = None
    for attr in ("to_tuple", "to_rgb", "rgb", "rgba"):
        if hasattr(color, attr):
            value = getattr(color, attr)
            rgb = value() if callable(value) else value
            break
    if rgb is None:
        text = str(color)
        if "r=" in text and "g=" in text and "b=" in text:
            try:
                cleaned = text
                if cleaned.startswith("Color(") and cleaned.endswith(")"):
                    cleaned = cleaned[len("Color(") : -1]
                parts = cleaned.replace(" ", "").split(",")
                vals = {
                    p.split("=")[0]: float(p.split("=")[1]) for p in parts if "=" in p
                }
                rgb = (vals.get("r"), vals.get("g"), vals.get("b"))
            except Exception:
                rgb = (0.5, 0.5, 0.5)
        else:
            rgb = (0.5, 0.5, 0.5)

    r, g, b = (rgb[0], rgb[1], rgb[2])

    def clamp_channel(val: float | None) -> int:
        if val is None:
            return 128
        return max(0, min(255, int(round(val * 255 if val <= 1 else val))))

    return f"#{clamp_channel(r):02x}{clamp_channel(g):02x}{clamp_channel(b):02x}"


def apply_3mf_face_colors(path: str, parts: list[Part]) -> None:
    wrapper = lib3mf.Wrapper()
    model = wrapper.CreateModel()
    reader = model.QueryReader("3mf")
    reader.ReadFromFile(path)

    mesh_objects: list = []
    mesh_iter = model.GetMeshObjects()
    while mesh_iter.MoveNext():
        mesh_objects.append(mesh_iter.GetCurrent())

    if not mesh_objects:
        raise RuntimeError("No mesh objects found in 3MF")

    color_group = model.AddColorGroup()
    resource_id = color_group.GetResourceID()

    def _add_color(hex_color: str) -> int:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        a = 255
        return color_group.AddColor(lib3mf.Color(r, g, b, a))

    color_index: dict[str, int] = {}

    def _find_part_by_label(label: str) -> Part:
        for part in parts:
            if part.label == label:
                return part
        raise RuntimeError(f"No part found with label '{label}'")

    for mesh in mesh_objects:
        part = _find_part_by_label(mesh.GetPartNumber())
        hex_color = _color_to_hex(part.color)
        if hex_color not in color_index:
            color_index[hex_color] = _add_color(hex_color)
        color_idx = color_index[hex_color]
        mesh.SetObjectLevelProperty(resource_id, color_idx)
        props = lib3mf.TriangleProperties()
        props.ResourceID = resource_id
        props.PropertyIDs[0] = color_idx
        props.PropertyIDs[1] = color_idx
        props.PropertyIDs[2] = color_idx

        tri_count = mesh.GetTriangleCount()
        for tri_index in range(tri_count):
            mesh.SetTriangleProperties(tri_index, props)

    writer = model.QueryWriter("3mf")
    writer.WriteToFile(path)
