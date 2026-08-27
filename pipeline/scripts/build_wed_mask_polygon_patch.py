"""Build a reversible WED override from one painted foreground mask.

The input mask is a world-anchored xN crop: white keeps the rendered object and
black identifies map pixels that must cover it.  The black component is traced,
quantized to logical x1 coordinates and stored in an explicitly empty WED wall
polygon slot with the native ``Cover animations`` flag.

The command is intentionally strict.  It requires the exact source WED hash,
the complete bytes of the empty polygon slot and the current lookup span of
every wall group being changed.  A diagnosis made against another game build
therefore fails closed instead of producing a stale override.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from build_wed_cover_animation_patch import (
    MANIFEST_SCHEMA,
    POLYGON_SIZE,
    WED_SIGNATURE,
    load_wed,
    sha256_bytes,
)


COVER_POLYGON_FLAGS = 0x09
DEFAULT_POLYGON_HEIGHT = 0xFF
WALL_GROUP_WIDTH = 640
WALL_GROUP_HEIGHT = 480


@dataclass(frozen=True)
class WedLayout:
    secondary_offset: int
    polygon_count: int
    polygon_offset: int
    vertex_offset: int
    wall_group_offset: int
    lookup_offset: int
    wall_group_count: int
    lookup_count: int
    vertex_count: int


@dataclass(frozen=True)
class WallGroupExpectation:
    index: int
    start: int
    count: int


def parse_pair(value: str) -> tuple[int, int]:
    try:
        left, right = value.split(",", 1)
        result = int(left, 0), int(right, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("utiliser la forme X,Y") from exc
    return result


def parse_wall_group(value: str) -> WallGroupExpectation:
    try:
        index_text, start_text, count_text = value.split(":", 2)
        result = WallGroupExpectation(
            index=int(index_text, 0),
            start=int(start_text, 0),
            count=int(count_text, 0),
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "--wall-group doit utiliser INDEX:START:COUNT"
        ) from exc
    if result.index < 0 or result.start < 0 or result.count < 0:
        raise argparse.ArgumentTypeError("les valeurs du wall group doivent être positives")
    return result


def parse_expected_polygon(value: str) -> bytes:
    try:
        result = bytes.fromhex(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--expected-polygon-hex doit être hexadécimal") from exc
    if len(result) != POLYGON_SIZE:
        raise argparse.ArgumentTypeError(
            f"--expected-polygon-hex doit décrire exactement {POLYGON_SIZE} octets"
        )
    return result


def parse_wed_layout(data: bytes) -> WedLayout:
    if len(data) < 0x20 or data[:8] != WED_SIGNATURE:
        raise ValueError("signature WED V1.3 invalide")
    overlay_count, _door_count, overlay_offset, secondary_offset = struct.unpack_from(
        "<IIII", data, 0x08
    )
    if overlay_count < 1 or overlay_offset > len(data) - 0x18:
        raise ValueError("overlay primaire WED absent ou hors fichier")
    width_tiles, height_tiles = struct.unpack_from("<HH", data, overlay_offset)
    if width_tiles < 1 or height_tiles < 1:
        raise ValueError("dimensions de l'overlay primaire WED invalides")
    if secondary_offset > len(data) - 0x14:
        raise ValueError("en-tête secondaire WED hors fichier")
    polygon_count, polygon_offset, vertex_offset, wall_group_offset, lookup_offset = (
        struct.unpack_from("<IIIII", data, secondary_offset)
    )
    wall_group_columns = math.ceil(width_tiles * 64 / WALL_GROUP_WIDTH)
    wall_group_rows = math.ceil(height_tiles * 64 / WALL_GROUP_HEIGHT)
    wall_group_count = wall_group_columns * wall_group_rows

    polygon_end = polygon_offset + polygon_count * POLYGON_SIZE
    wall_group_end = wall_group_offset + wall_group_count * 4
    if not (0 <= wall_group_offset <= wall_group_end <= len(data)):
        raise ValueError("table des wall groups WED hors fichier")
    if not (0 <= polygon_offset <= polygon_end <= len(data)):
        raise ValueError("table des polygones WED hors fichier")
    if polygon_end != lookup_offset:
        raise ValueError("la table lookup ne suit pas exactement les polygones WED")
    if not (lookup_offset <= vertex_offset <= len(data)):
        raise ValueError("table lookup ou table des sommets WED hors fichier")
    if (vertex_offset - lookup_offset) % 2:
        raise ValueError("taille impaire de la table lookup WED")
    if (len(data) - vertex_offset) % 4:
        raise ValueError("taille invalide de la table des sommets WED")

    lookup_count = (vertex_offset - lookup_offset) // 2
    vertex_count = (len(data) - vertex_offset) // 4
    previous_end = 0
    for group_index in range(wall_group_count):
        start, count = struct.unpack_from("<HH", data, wall_group_offset + group_index * 4)
        if start != previous_end or start + count > lookup_count:
            raise ValueError(f"wall group {group_index}: plage lookup non contiguë")
        previous_end = start + count
    if previous_end != lookup_count:
        raise ValueError("les wall groups ne consomment pas toute la table lookup")

    return WedLayout(
        secondary_offset=secondary_offset,
        polygon_count=polygon_count,
        polygon_offset=polygon_offset,
        vertex_offset=vertex_offset,
        wall_group_offset=wall_group_offset,
        lookup_offset=lookup_offset,
        wall_group_count=wall_group_count,
        lookup_count=lookup_count,
        vertex_count=vertex_count,
    )


def _binary_mask(path: Path, threshold: int) -> tuple[list[list[bool]], dict[str, object]]:
    if not 0 <= threshold <= 255:
        raise ValueError("le seuil du masque doit être compris entre 0 et 255")
    with Image.open(path) as opened:
        rgba = opened.convert("RGBA")
        width, height = rgba.size
        if width < 1 or height < 1 or width * height > 16_777_216:
            raise ValueError("dimensions de masque invalides ou excessives")
        flattened = getattr(rgba, "get_flattened_data", None)
        pixels = list(flattened() if flattened is not None else rgba.getdata())
    if any(alpha != 255 for _red, _green, _blue, alpha in pixels):
        raise ValueError("le masque doit être aplati et entièrement opaque")
    if any(red != green or green != blue for red, green, blue, _alpha in pixels):
        raise ValueError("le masque doit être en niveaux de gris")
    mask = [
        [pixels[y * width + x][0] <= threshold for x in range(width)]
        for y in range(height)
    ]
    black_count = sum(sum(row) for row in mask)
    if black_count == 0 or black_count == width * height:
        raise ValueError("le masque doit contenir du blanc et du noir")

    visited: set[tuple[int, int]] = set()
    components = 0
    for y in range(height):
        for x in range(width):
            if not mask[y][x] or (x, y) in visited:
                continue
            components += 1
            queue = deque([(x, y)])
            visited.add((x, y))
            while queue:
                current_x, current_y = queue.popleft()
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if (
                        0 <= next_x < width
                        and 0 <= next_y < height
                        and mask[next_y][next_x]
                        and (next_x, next_y) not in visited
                    ):
                        visited.add((next_x, next_y))
                        queue.append((next_x, next_y))
    if components != 1:
        raise ValueError(f"le masque noir doit former une seule composante, trouvé : {components}")

    return mask, {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": width,
        "height": height,
        "threshold": threshold,
        "black_pixels": black_count,
    }


def _trace_boundary(mask: list[list[bool]]) -> list[tuple[int, int]]:
    height = len(mask)
    width = len(mask[0])
    edges: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for y, row in enumerate(mask):
        for x, black in enumerate(row):
            if not black:
                continue
            if y == 0 or not mask[y - 1][x]:
                edges[(x, y)].append((x + 1, y))
            if x == width - 1 or not row[x + 1]:
                edges[(x + 1, y)].append((x + 1, y + 1))
            if y == height - 1 or not mask[y + 1][x]:
                edges[(x + 1, y + 1)].append((x, y + 1))
            if x == 0 or not row[x - 1]:
                edges[(x, y + 1)].append((x, y))
    if not edges or any(len(targets) != 1 for targets in edges.values()):
        raise ValueError("le contour du masque est ambigu")

    start = min(edges)
    boundary = [start]
    current = start
    consumed = 0
    while True:
        targets = edges.get(current)
        if not targets:
            raise ValueError("le contour du masque est ouvert")
        current = targets[0]
        consumed += 1
        if current == start:
            break
        if consumed > len(edges):
            raise ValueError("boucle invalide dans le contour du masque")
        boundary.append(current)
    if consumed != len(edges):
        raise ValueError("le masque contient un trou ou un second contour")
    return boundary


def _cross(a: tuple[int, int], b: tuple[int, int], c: tuple[int, int]) -> int:
    return (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])


def _clean_closed(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    cleaned: list[tuple[int, int]] = []
    for point in points:
        if not cleaned or point != cleaned[-1]:
            cleaned.append(point)
    if len(cleaned) > 1 and cleaned[0] == cleaned[-1]:
        cleaned.pop()
    changed = True
    while changed and len(cleaned) >= 3:
        changed = False
        result: list[tuple[int, int]] = []
        for index, point in enumerate(cleaned):
            if _cross(cleaned[index - 1], point, cleaned[(index + 1) % len(cleaned)]) == 0:
                changed = True
            else:
                result.append(point)
        cleaned = result
    return cleaned


def _distance_to_segment(
    point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]
) -> float:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if dx == 0 and dy == 0:
        return math.hypot(point[0] - start[0], point[1] - start[1])
    position = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
    position = max(0.0, min(1.0, position))
    projected_x = start[0] + position * dx
    projected_y = start[1] + position * dy
    return math.hypot(point[0] - projected_x, point[1] - projected_y)


def _rdp(points: list[tuple[int, int]], tolerance: float) -> list[tuple[int, int]]:
    if len(points) <= 2:
        return points
    maximum = -1.0
    maximum_index = 0
    for index in range(1, len(points) - 1):
        distance = _distance_to_segment(points[index], points[0], points[-1])
        if distance > maximum:
            maximum = distance
            maximum_index = index
    if maximum > tolerance:
        left = _rdp(points[: maximum_index + 1], tolerance)
        right = _rdp(points[maximum_index:], tolerance)
        return left[:-1] + right
    return [points[0], points[-1]]


def _simplify_closed(points: list[tuple[int, int]], tolerance: float) -> list[tuple[int, int]]:
    points = _clean_closed(points)
    if len(points) < 3 or tolerance <= 0:
        return points
    anchor = min(range(len(points)), key=lambda index: points[index])
    rotated = points[anchor:] + points[:anchor]
    opposite = max(
        range(1, len(rotated)),
        key=lambda index: (
            (rotated[index][0] - rotated[0][0]) ** 2
            + (rotated[index][1] - rotated[0][1]) ** 2
        ),
    )
    first = _rdp(rotated[: opposite + 1], tolerance)
    second = _rdp(rotated[opposite:] + [rotated[0]], tolerance)
    return _clean_closed(first[:-1] + second[:-1])


def _segments_intersect(
    a: tuple[int, int],
    b: tuple[int, int],
    c: tuple[int, int],
    d: tuple[int, int],
) -> bool:
    def orientation(p: tuple[int, int], q: tuple[int, int], r: tuple[int, int]) -> int:
        value = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
        return (value > 0) - (value < 0)

    return orientation(a, b, c) != orientation(a, b, d) and orientation(c, d, a) != orientation(c, d, b)


def validate_polygon(vertices: list[tuple[int, int]]) -> None:
    if len(vertices) < 3:
        raise ValueError("le polygone doit contenir au moins trois sommets")
    if len(vertices) > 65535:
        raise ValueError("le polygone dépasse la limite WED de sommets")
    if len(vertices) != len(set(vertices)):
        raise ValueError("le polygone contient des sommets dupliqués")
    if any(not 0 <= coordinate <= 32767 for point in vertices for coordinate in point):
        raise ValueError("un sommet est hors des coordonnées WED positives")
    for first in range(len(vertices)):
        a = vertices[first]
        b = vertices[(first + 1) % len(vertices)]
        for second in range(first + 1, len(vertices)):
            if second in (first, (first + 1) % len(vertices)):
                continue
            if first == 0 and second == len(vertices) - 1:
                continue
            c = vertices[second]
            d = vertices[(second + 1) % len(vertices)]
            if _segments_intersect(a, b, c, d):
                raise ValueError("le polygone s'auto-intersecte")
    area2 = sum(
        vertices[index][0] * vertices[(index + 1) % len(vertices)][1]
        - vertices[(index + 1) % len(vertices)][0] * vertices[index][1]
        for index in range(len(vertices))
    )
    if area2 == 0:
        raise ValueError("le polygone a une aire nulle")


def mask_to_world_polygon(
    mask_path: Path,
    origin_x1: tuple[int, int],
    scale: int,
    threshold: int,
    simplify_tolerance_x1: float,
) -> tuple[list[tuple[int, int]], dict[str, object]]:
    if scale < 1 or scale > 16:
        raise ValueError("l'échelle du masque doit être comprise entre 1 et 16")
    if simplify_tolerance_x1 < 0 or simplify_tolerance_x1 > 8:
        raise ValueError("tolérance de simplification hors plage")
    mask, details = _binary_mask(mask_path, threshold)
    boundary = _trace_boundary(mask)
    quantized = [
        ((x + scale // 2) // scale, (y + scale // 2) // scale)
        for x, y in boundary
    ]
    local_polygon = _simplify_closed(quantized, simplify_tolerance_x1)
    world_polygon = [
        (origin_x1[0] + x, origin_x1[1] + y) for x, y in local_polygon
    ]
    validate_polygon(world_polygon)

    width = int(details["width"])
    height = int(details["height"])
    rendered = Image.new("1", (width, height), 0)
    ImageDraw.Draw(rendered).polygon(
        [(x * scale, y * scale) for x, y in local_polygon], fill=1
    )
    flattened = getattr(rendered, "get_flattened_data", None)
    rendered_pixels = list(flattened() if flattened is not None else rendered.getdata())
    source_pixels = [pixel for row in mask for pixel in row]
    intersection = sum(bool(a) and bool(b) for a, b in zip(source_pixels, rendered_pixels))
    union = sum(bool(a) or bool(b) for a, b in zip(source_pixels, rendered_pixels))
    false_negative = sum(bool(a) and not bool(b) for a, b in zip(source_pixels, rendered_pixels))
    false_positive = sum(not bool(a) and bool(b) for a, b in zip(source_pixels, rendered_pixels))
    iou = intersection / union
    if iou < 0.95:
        raise ValueError(f"fidélité du polygone insuffisante après quantification : IoU {iou:.6f}")

    details.update({
        "origin_x1": list(origin_x1),
        "scale": scale,
        "source_boundary_vertices": len(boundary),
        "polygon_vertices": len(world_polygon),
        "simplify_tolerance_x1": simplify_tolerance_x1,
        "intersection_over_union": iou,
        "false_negative_pixels_xN": false_negative,
        "false_positive_pixels_xN": false_positive,
        "world_bbox": [
            min(x for x, _y in world_polygon),
            min(y for _x, y in world_polygon),
            max(x for x, _y in world_polygon),
            max(y for _x, y in world_polygon),
        ],
    })
    return world_polygon, details


def add_wall_polygon(
    source: bytes,
    polygon_index: int,
    expected_polygon: bytes,
    wall_groups: list[WallGroupExpectation],
    vertices: list[tuple[int, int]],
) -> tuple[bytes, dict[str, object]]:
    layout = parse_wed_layout(source)
    validate_polygon(vertices)
    if not 0 <= polygon_index < layout.polygon_count:
        raise ValueError("index du polygone hors table")
    if not wall_groups:
        raise ValueError("au moins un wall group doit être fourni")
    indexes = [group.index for group in wall_groups]
    if len(indexes) != len(set(indexes)):
        raise ValueError("un wall group est demandé plusieurs fois")

    polygon_file_offset = layout.polygon_offset + polygon_index * POLYGON_SIZE
    actual_polygon = source[polygon_file_offset: polygon_file_offset + POLYGON_SIZE]
    if actual_polygon != expected_polygon:
        raise ValueError(
            f"polygone {polygon_index}: octets source différents de la valeur attendue"
        )
    _start, point_count, _flags, _height, _left, _right, _top, _bottom = struct.unpack(
        "<IIBBHHHH", actual_polygon
    )
    if point_count != 0:
        raise ValueError(f"polygone {polygon_index}: le slot n'est pas vide")

    lookup = list(struct.unpack_from(f"<{layout.lookup_count}H", source, layout.lookup_offset))
    if polygon_index in lookup:
        raise ValueError(f"polygone {polygon_index}: déjà référencé par un wall group")
    expected_by_index = {group.index: group for group in wall_groups}
    new_lookup: list[int] = []
    new_group_values: list[tuple[int, int]] = []
    for group_index in range(layout.wall_group_count):
        start, count = struct.unpack_from(
            "<HH", source, layout.wall_group_offset + group_index * 4
        )
        expectation = expected_by_index.get(group_index)
        if expectation is not None and (start, count) != (expectation.start, expectation.count):
            raise ValueError(
                f"wall group {group_index}: plage {start}:{count}, "
                f"{expectation.start}:{expectation.count} attendue"
            )
        values = lookup[start: start + count]
        if expectation is not None:
            insertion = next(
                (index for index, value in enumerate(values) if value > polygon_index),
                len(values),
            )
            values = values[:insertion] + [polygon_index] + values[insertion:]
        new_group_values.append((len(new_lookup), len(values)))
        new_lookup.extend(values)

    insertion_bytes = 2 * len(wall_groups)
    new_vertex_offset = layout.vertex_offset + insertion_bytes
    prefix = bytearray(source[: layout.lookup_offset])
    struct.pack_into("<I", prefix, layout.secondary_offset + 0x08, new_vertex_offset)
    for group_index, (start, count) in enumerate(new_group_values):
        struct.pack_into(
            "<HH", prefix, layout.wall_group_offset + group_index * 4, start, count
        )

    left = min(x for x, _y in vertices)
    right = max(x for x, _y in vertices)
    top = min(y for _x, y in vertices)
    bottom = max(y for _x, y in vertices)
    struct.pack_into(
        "<IIBBHHHH",
        prefix,
        polygon_file_offset,
        layout.vertex_count,
        len(vertices),
        COVER_POLYGON_FLAGS,
        DEFAULT_POLYGON_HEIGHT,
        left,
        right,
        top,
        bottom,
    )
    lookup_bytes = struct.pack(f"<{len(new_lookup)}H", *new_lookup)
    vertex_bytes = b"".join(struct.pack("<hh", x, y) for x, y in vertices)
    output = bytes(prefix) + lookup_bytes + source[layout.vertex_offset:] + vertex_bytes

    output_layout = parse_wed_layout(output)
    if output_layout.vertex_offset != new_vertex_offset:
        raise RuntimeError("offset de sommets WED incorrect après génération")
    if output_layout.lookup_count != layout.lookup_count + len(wall_groups):
        raise RuntimeError("taille lookup WED incorrecte après génération")
    if output_layout.vertex_count != layout.vertex_count + len(vertices):
        raise RuntimeError("taille de la table des sommets WED incorrecte après génération")
    if output[new_vertex_offset: new_vertex_offset + (len(source) - layout.vertex_offset)] != source[layout.vertex_offset:]:
        raise RuntimeError("les sommets WED existants ont été modifiés")

    return output, {
        "polygon_index": polygon_index,
        "polygon_file_offset": f"0x{polygon_file_offset:X}",
        "original_polygon_hex": actual_polygon.hex(),
        "flags": COVER_POLYGON_FLAGS,
        "flags_hex": f"0x{COVER_POLYGON_FLAGS:02X}",
        "height": DEFAULT_POLYGON_HEIGHT,
        "starting_vertex": layout.vertex_count,
        "vertex_count": len(vertices),
        "vertices": [list(point) for point in vertices],
        "bbox": [left, top, right, bottom],
        "wall_groups": [
            {
                "index": group.index,
                "original_start": group.start,
                "original_count": group.count,
            }
            for group in wall_groups
        ],
        "lookup_entries_added": len(wall_groups),
        "source_vertex_offset": layout.vertex_offset,
        "output_vertex_offset": new_vertex_offset,
    }


def build(
    area: str,
    output_dir: Path,
    mask_path: Path,
    mask_origin_x1: tuple[int, int],
    mask_scale: int,
    mask_threshold: int,
    simplify_tolerance_x1: float,
    polygon_index: int,
    expected_polygon: bytes,
    wall_groups: list[WallGroupExpectation],
    expected_source_sha256: str,
) -> dict[str, object]:
    area = area.upper()
    if len(area) > 8 or not area.isascii() or not area.isalnum():
        raise ValueError(f"resref de zone invalide : {area!r}")
    source, source_bif = load_wed(area)
    source_sha256 = sha256_bytes(source)
    if source_sha256.lower() != expected_source_sha256.lower():
        raise ValueError(
            f"{area}: SHA-256 source {source_sha256}, {expected_source_sha256.lower()} attendu"
        )
    vertices, mask_details = mask_to_world_polygon(
        mask_path,
        mask_origin_x1,
        mask_scale,
        mask_threshold,
        simplify_tolerance_x1,
    )
    patched, patch_details = add_wall_polygon(
        source, polygon_index, expected_polygon, wall_groups, vertices
    )

    output_dir = output_dir.resolve()
    output_path = output_dir / f"{area}.WED"
    manifest_path = output_dir / "manifest.json"
    if output_path.exists() and output_path.read_bytes() != patched:
        raise RuntimeError(f"destination WED existante différente : {output_path}")

    manifest: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "status": "completed",
        "area": area,
        "purpose": "native-wed-painted-mask-polygon-test",
        "qa_status": "pending-ingame",
        "files": {
            output_path.name: {
                "bytes": len(patched),
                "sha256": sha256_bytes(patched),
            }
        },
        "wed_patch": {
            "source": "KEY/BIF",
            "source_bif": source_bif,
            "source_bytes": len(source),
            "source_sha256": source_sha256,
            "output_sha256": sha256_bytes(patched),
            "mask": mask_details,
            "polygon": patch_details,
        },
        "compatibility": {
            "x1_maps": "native WED logical coordinates; no TIS or overlay change",
            "x4_maps": "same logical WED polygon consumed by the native bridge",
            "saves": "no ARE or serialized schema change",
            "runtime_memory": "no xN texture or registry payload added",
            "rollback": "Restore-AreaOverrideAssets.ps1 with the install backup",
        },
    }
    rendered_manifest = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if output_path.exists() and output_path.read_bytes() != patched:
        raise RuntimeError(f"destination WED existante différente : {output_path}")
    if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != rendered_manifest:
        raise RuntimeError(f"manifeste existant différent : {manifest_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(patched)
    manifest_path.write_text(rendered_manifest, encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", help="resref WED de la zone, par exemple AR0516")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--mask-png", required=True, type=Path)
    parser.add_argument("--mask-origin-x1", required=True, type=parse_pair)
    parser.add_argument("--mask-scale", type=int, default=4)
    parser.add_argument("--mask-threshold", type=int, default=127)
    parser.add_argument("--simplify-tolerance-x1", type=float, default=0.75)
    parser.add_argument("--polygon-index", required=True, type=int)
    parser.add_argument("--expected-polygon-hex", required=True, type=parse_expected_polygon)
    parser.add_argument(
        "--wall-group",
        action="append",
        required=True,
        type=parse_wall_group,
        help="wall group et plage lookup source INDEX:START:COUNT",
    )
    parser.add_argument("--expected-source-sha256", required=True)
    args = parser.parse_args()
    manifest = build(
        area=args.area,
        output_dir=args.output_dir,
        mask_path=args.mask_png,
        mask_origin_x1=args.mask_origin_x1,
        mask_scale=args.mask_scale,
        mask_threshold=args.mask_threshold,
        simplify_tolerance_x1=args.simplify_tolerance_x1,
        polygon_index=args.polygon_index,
        expected_polygon=args.expected_polygon_hex,
        wall_groups=args.wall_group,
        expected_source_sha256=args.expected_source_sha256,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
