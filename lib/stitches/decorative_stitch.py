import math

import shapely.geometry as shgeo

from ..utils.geometry import Point
from .running_stitch import running_stitch


def decorative_stitch(path, pattern_points, stitch_length, tolerance):
    """Tile pattern_points along path and return a list of Stitch objects.

    The pattern's first and last points are anchors. Each tile maps the
    anchor-to-anchor baseline onto exactly one stitch_length of the path,
    scaling all perpendicular offsets proportionally.

    stitch_length may be a list (multi-value patterns) or a scalar; the first
    value is used as the tile length.
    """
    tile_length = stitch_length[0] if isinstance(stitch_length, list) else stitch_length

    if len(pattern_points) < 2 or len(path) < 2:
        return running_stitch(path, stitch_length, tolerance, False, 0, "")

    p0 = pattern_points[0]
    pn = pattern_points[-1]
    baseline_dx = pn[0] - p0[0]
    baseline_dy = pn[1] - p0[1]
    baseline_length = math.hypot(baseline_dx, baseline_dy)

    if baseline_length < 1e-6:
        return running_stitch(path, stitch_length, tolerance, False, 0, "")

    # Unit vectors along and perpendicular to the pattern baseline
    bx = baseline_dx / baseline_length
    by = baseline_dy / baseline_length
    nx = -by
    ny = bx

    # Scale factor so one tile spans exactly tile_length on the path
    pattern_scale = tile_length / baseline_length

    # Precompute each point's (along, perp) offset, scaled to SVG pixel units
    offsets = []
    for px, py in pattern_points:
        dx = px - p0[0]
        dy = py - p0[1]
        along = (dx * bx + dy * by) * pattern_scale
        perp = (dx * nx + dy * ny) * pattern_scale
        offsets.append((along, perp))

    coords = [(pt.x, pt.y) for pt in path]
    line = shgeo.LineString(coords)
    total_length = line.length

    if total_length < 1e-6:
        return []

    world_points = []
    tile_start_dist = 0.0
    first_tile = True

    while tile_start_dist < total_length - 1e-6:
        tile_end_dist = tile_start_dist + tile_length
        clamped_end = min(tile_end_dist, total_length)
        seg_length = clamped_end - tile_start_dist

        if seg_length < 1e-6:
            break

        # Compress partial last tile so it still reaches the endpoint
        partial_scale = seg_length / tile_length

        ts = line.interpolate(tile_start_dist)
        te = line.interpolate(clamped_end)

        seg_dx = te.x - ts.x
        seg_dy = te.y - ts.y
        seg_len = math.hypot(seg_dx, seg_dy)

        if seg_len < 1e-9:
            tile_start_dist += tile_length
            continue

        # Local tile frame: forward along path, normal perpendicular
        fw_x = seg_dx / seg_len
        fw_y = seg_dy / seg_len
        nw_x = -fw_y
        nw_y = fw_x

        # Skip point 0 on subsequent tiles — identical to the previous tile's last point
        start_idx = 1 if not first_tile else 0
        first_tile = False

        for along, perp in offsets[start_idx:]:
            wx = ts.x + fw_x * (along * partial_scale) + nw_x * (perp * partial_scale)
            wy = ts.y + fw_y * (along * partial_scale) + nw_y * (perp * partial_scale)
            world_points.append(Point(wx, wy))

        tile_start_dist += tile_length

    if not world_points:
        return running_stitch(path, stitch_length, tolerance, False, 0, "")

    return world_points
