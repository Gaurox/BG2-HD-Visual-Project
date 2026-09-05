"""Build power-of-two upscaled TIS + PVRZ content for an Infinity Engine area.

Keeps the WED tile grid untouched: the tileset stays at the same tile count and
the same atlas layout, but every tile is authored at a supported power-of-two
multiple of 64x64 and the TIS header declares that tile dimension, which InfinityEngine-Enhancer
reads to expand UV sampling while the engine keeps its 64x64 world geometry.
"""
import io
import os
import struct
import sys
import zlib

import numpy as np
from PIL import Image, ImageFilter

from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from mos_decode import decode_pvrz_page

Image.MAX_IMAGE_PIXELS = None

WED_TYPE, TIS_TYPE, PVRZ_TYPE = 0x03E9, 0x03EB, 0x0404
TILE = 64
# Scale 1 is intentional: it permits a lossless-size DXT5 re-pack when a
# legacy liquid family needs only its source alpha repaired.  It is not an AI
# upscale mode.
SUPPORTED_SCALES = (1, 2, 4, 8)
PAD = 4          # replicated border around each tile, kills bilinear seams
# Taille des pages PVRZ. Le moteur lit les dimensions dans l'en-tete PVR et
# accepte des tailles variables (vanilla melange 1024x1024, 256x1024, 64x256...).
#
# Regle de production (2026-08-18) :
#   - 2048 par defaut ;
#   - 4096 UNIQUEMENT si 2048 depasse la limite de nommage du prefixe (RESREF_MAX) ;
#   - si 4096 ne suffit pas : echec explicite du build, AUCUN repli au-dela.
# 8192 est volontairement absent des candidats : une page plus grande ne change
# aucun pixel, seulement la disposition d'atlas, donc l'agrandir sans necessite
# de nommage n'apporte rien. Un depassement a 4096 (>22500 tuiles en x4 pour une
# variante nuit) signalerait un probleme en amont qui doit etre vu, pas absorbe.
# 4096 est valide en jeu sur AR0900/AR0900N (jour et nuit) le 2026-08-18.
# IEE_PVRZ_PAGE_SIZE force une taille fixe et desactive cette montee automatique ;
# le garde-fou de nommage reste actif dans tous les cas.
PAGE_SIZE_ENV = os.environ.get("IEE_PVRZ_PAGE_SIZE")
PAGE_SIZE = int(PAGE_SIZE_ENV) if PAGE_SIZE_ENV else 2048
PAGE_SIZE_CANDIDATES = (2048, 4096)
# CResRef fait 8 octets dans l'ABI du moteur (static_assert dans la DLL) : le nom
# d'une page est donc plafonne a 8 caracteres, prefixe compris.
RESREF_MAX = 8
PVR_MAGIC = 0x03525650


def build(area, upscaled_png, out_dir, secondary_png=None,
          transparent_full_water_base=False, soften_water_contours=False,
          water_contour_feather=0.0, preserve_source_page_layout=False,
          wed_regions_1024=False, dxt1=False, soften_all_alpha_contours=True,
          alpha_contour_feather=0.0):
    bif_entries, res_entries = load_key()
    wed_by = {r[0].upper(): r for r in res_entries if r[1] == WED_TYPE}
    tis_by = {r[0].upper(): r for r in res_entries if r[1] == TIS_TYPE}
    pvrz_by = {r[0].upper(): r for r in res_entries if r[1] == PVRZ_TYPE}

    # --- WED overlay 0 -------------------------------------------------
    wdata, _ = resolve_resource(bif_entries, wed_by[area][2])
    _, _, off_overlays = struct.unpack_from("<III", wdata, 8)
    ov_w, ov_h = struct.unpack_from("<HH", wdata, off_overlays)
    tileset_ref = wdata[off_overlays + 4:off_overlays + 12].split(b"\0")[0].decode("ascii")
    off_tilemap, off_lookup = struct.unpack_from("<II", wdata, off_overlays + 0x10)

    cell_primary = []
    secondary_to_cell = {}
    water_contour_secondary_tiles = set()
    # Explicit, area-specific repair mode: some legacy EE areas author open
    # water as fully opaque base tiles even though the WED marks the cell as
    # receiving a liquid overlay.  They cover the animated underlay as square
    # static blocks.  Only tile IDs used *exclusively* by water cells with no
    # secondary art are eligible; partially transparent shoreline/decor tiles
    # remain controlled by their original alpha contour.
    overlay_count = struct.unpack_from("<I", wdata, 8)[0]
    liquid_overlay_bits = 0
    # WTSWAM, WTSEW and WTOIL keep their legacy generic overlay at stock x1;
    # only the area-alpha contour and liquid-only base tiles use this repair.
    # An overlay override creates repeated visible cells in map/automap paths.
    water_prefixes = ("WTWAVE", "WTRIV", "WTPOOL", "WTLAK", "WTFALL", "WTURN", "YSPOOL", "YSRIV", "YSWAVE", "WTSWAM", "WTSEW", "WTOIL", "WTLAV")
    for overlay_index in range(1, overlay_count):
        overlay_offset = off_overlays + overlay_index * 24
        overlay_ref = wdata[overlay_offset + 4:overlay_offset + 12].split(b"\0")[0].decode("ascii").upper()
        if overlay_ref.startswith(water_prefixes):
            liquid_overlay_bits |= 1 << overlay_index
    if transparent_full_water_base and not liquid_overlay_bits:
        raise SystemExit(
            f"{area}: --transparent-full-water-base requires a recognised liquid WED overlay")
    primary_cell_uses = {}
    full_water_base_uses = set()
    for i in range(ov_w * ov_h):
        start, _cnt, sec, flags = struct.unpack_from("<HHHB3x", wdata, off_tilemap + i * 10)
        primary = struct.unpack_from("<H", wdata, off_lookup + start * 2)[0]
        cell_primary.append(primary)
        primary_cell_uses.setdefault(primary, []).append((flags, sec))
        if flags & liquid_overlay_bits and sec == 0xFFFF:
            full_water_base_uses.add(primary)
        if sec != 0xFFFF:
            secondary_to_cell.setdefault(sec, i)
            # Fountain/pool cells carry their painted water silhouette in the
            # secondary tile.  Preserve and soften that alpha alongside the
            # primary contour; RGB black is only the transparent-key colour.
            if flags & liquid_overlay_bits:
                water_contour_secondary_tiles.add(sec)

    water_only_base_tiles = {
        tile_id for tile_id in full_water_base_uses
        if all(flags & liquid_overlay_bits and secondary == 0xFFFF
               for flags, secondary in primary_cell_uses[tile_id])
    }

    # tile index -> cell index, for tiles that a cell draws directly
    tile_to_cell = {}
    for cell, tid in enumerate(cell_primary):
        tile_to_cell.setdefault(tid, cell)

    water_contour_base_tiles = {
        tid for tid, cell in tile_to_cell.items()
        if struct.unpack_from("<HHHB3x", wdata, off_tilemap + cell * 10)[3] & liquid_overlay_bits
    }

    # --- original TIS --------------------------------------------------
    tdata, tile_count, entry_size, _ = resolve_tileset_resource(bif_entries, tis_by[tileset_ref.upper()][2])
    if entry_size != 12:
        raise SystemExit(f"{area}: not a PVRZ-based tileset (entry size {entry_size})")

    entries = [struct.unpack_from("<3I", tdata, i * 12) for i in range(tile_count)]
    # --- original PVRZ pages (needed for tiles with no upscaled source) --
    prefix = tileset_ref[0] + tileset_ref[2:]
    used_pages = sorted({p for p, _, _ in entries if p != 0xFFFFFFFF})
    orig_pages, page_size, page_fmt = {}, {}, {}
    for page in used_pages:
        name = f"{prefix}{page:02d}".upper()
        raw, _ = resolve_resource(bif_entries, pvrz_by[name][2])
        dec = zlib.decompress(raw[4:])
        _, _, pf_low, _, _, _, h, w, *_ = struct.unpack_from("<13I", dec, 0)
        page_size[page] = (w, h)
        page_fmt[page] = pf_low
        orig_pages[page] = decode_pvrz_page(raw)

    src = Image.open(upscaled_png).convert("RGB")
    scales = [
        scale for scale in SUPPORTED_SCALES
        if src.size == (ov_w * TILE * scale, ov_h * TILE * scale)
    ]
    if len(scales) != 1:
        expected = [f"{ov_w * TILE * scale}x{ov_h * TILE * scale}" for scale in SUPPORTED_SCALES]
        raise SystemExit(f"{area}: upscaled image is {src.size}, expected one of {', '.join(expected)}")
    scale = scales[0]
    new_tile = TILE * scale
    expected = (ov_w * new_tile, ov_h * new_tile)

    # Optional second render carrying the upscaled door (secondary) art.
    sec_src = None
    if secondary_png:
        sec_src = Image.open(secondary_png).convert("RGB")
        if sec_src.size != expected:
            raise SystemExit(
                f"{area}: secondary image is {sec_src.size}, expected {expected}")

    # --- gather tile images ---------------------------------------------
    # SeedVR receives RGB only.  The source alpha is therefore always restored
    # rather than inferred from black RGB.  A binary x1 mask scaled with nearest
    # creates hard four-pixel stairs at x4; smooth every non-opaque source mask
    # bilinearly by default, not only masks that belong to a liquid cell.
    def source_alpha(page, u, v, smooth=False, feather_radius=0.0):
        alpha = orig_pages[page].crop((u, v, u + TILE, v + TILE)).getchannel("A")
        has_alpha_contour = alpha.getextrema() != (255, 255)
        if smooth and has_alpha_contour and feather_radius > 0:
            # Radius is expressed in source (x1) pixels.  Blurring before the
            # x2/x4 resize creates a wide, continuous DXT5 alpha transition
            # without altering the SeedVR colour art or the map geometry.
            alpha = alpha.filter(ImageFilter.GaussianBlur(radius=feather_radius))
        return alpha.resize(
            (new_tile, new_tile),
            Image.Resampling.BILINEAR if smooth and has_alpha_contour else Image.Resampling.NEAREST,
        )

    def with_source_alpha(color, page, u, v, smooth=False, feather_radius=0.0):
        alpha = source_alpha(page, u, v, smooth=smooth, feather_radius=feather_radius)
        tile = color.convert("RGBA")
        tile.putalpha(alpha)
        return tile

    def is_fully_opaque_source(page, u, v):
        return orig_pages[page].crop((u, v, u + TILE, v + TILE)).getchannel("A").getextrema() == (255, 255)

    tiles = {}
    from_upscale = from_resample = black = released_full_water_bases = 0
    for idx, (page, u, v) in enumerate(entries):
        if page == 0xFFFFFFFF:
            black += 1
            continue

        cell = tile_to_cell.get(idx)
        if cell is not None:
            col, row = cell % ov_w, cell // ov_w
            color = src.crop((col * new_tile, row * new_tile,
                              (col + 1) * new_tile, (row + 1) * new_tile))
            water_contour = soften_water_contours and idx in water_contour_base_tiles
            tile_img = with_source_alpha(
                color, page, u, v,
                smooth=soften_all_alpha_contours or water_contour,
                # A liquid-specific feather must take precedence over the
                # global bilinear default.  Otherwise --water-contour-feather
                # was silently ignored whenever global alpha smoothing was on.
                feather_radius=(water_contour_feather if water_contour and water_contour_feather > 0
                                else (alpha_contour_feather if soften_all_alpha_contours else 0.0)),
            )
            if (transparent_full_water_base and idx in water_only_base_tiles and
                    is_fully_opaque_source(page, u, v)):
                tile_img.putalpha(0)
                released_full_water_bases += 1
            from_upscale += 1
        elif sec_src is not None and idx in secondary_to_cell:
            # Conditional art (doors, water contours, etc.), taken from the
            # second upscaled render at its own cell.  Its original alpha is
            # essential: black can mean transparent liquid reveal, not black art.
            cell = secondary_to_cell[idx]
            col, row = cell % ov_w, cell // ov_w
            color = sec_src.crop((col * new_tile, row * new_tile,
                                  (col + 1) * new_tile, (row + 1) * new_tile))
            water_contour = soften_water_contours and idx in water_contour_secondary_tiles
            tile_img = with_source_alpha(
                color, page, u, v,
                smooth=soften_all_alpha_contours or water_contour,
                feather_radius=(water_contour_feather if water_contour and water_contour_feather > 0
                                else (alpha_contour_feather if soften_all_alpha_contours else 0.0)),
            )
            from_upscale += 1
        else:
            # No upscaled source for this tile: resample the original 64x64 so
            # the tileset stays internally consistent.
            original = orig_pages[page].crop((u, v, u + TILE, v + TILE))
            color = original.convert("RGB").resize((new_tile, new_tile), Image.LANCZOS)
            tile_img = color.convert("RGBA")
            tile_img.putalpha(source_alpha(
                page, u, v, smooth=soften_all_alpha_contours,
                feather_radius=alpha_contour_feather if soften_all_alpha_contours else 0.0))
            from_resample += 1
        tiles[idx] = tile_img

    print(f"tiles: {from_upscale} from upscale, {from_resample} resampled, {black} black")
    if soften_all_alpha_contours:
        print("alpha repair: every non-opaque source mask bilinear-smoothed")
        if alpha_contour_feather > 0:
            print(f"alpha repair: global contour feather radius {alpha_contour_feather:g} source pixels")
    if transparent_full_water_base:
        print(f"water repair: {released_full_water_bases} fully opaque liquid-only base tiles released "
              f"({len(water_only_base_tiles)} IDs structurally eligible, including black sentinels)")
    if soften_water_contours:
        print(f"water repair: {len(water_contour_base_tiles)} base water contour tile IDs alpha-smoothed")
        print(f"water repair: {len(water_contour_secondary_tiles)} secondary water contour tile IDs alpha-smoothed")
        if water_contour_feather > 0:
            print(f"water repair: contour feather radius {water_contour_feather:g} source pixels")

    # --- pack pages ------------------------------------------------------
    # Most areas use a compact atlas with a small replicated border to avoid
    # bilinear seams.  A few legacy areas build render batches keyed to their
    # original PVRZ page/index layout; preserve_source_page_layout is the
    # compatibility mode for those areas.  It keeps each source page and every
    # source tile slot stable, simply scaling its coordinates into a larger
    # page.  At x2, an original 1024px 16x16 atlas becomes a 2048px atlas.
    placement = {}
    if wed_regions_1024:
        # EE's stock PVRZ paths are documented and implemented around a
        # 1024px texture ceiling.  The enhanced tile hook handles larger
        # pixels in its per-tile draw path, but the automap/bulk paths still
        # batch the original 64px page regions.  Keep x2 map regions within
        # a 1024px page (8x8 128px tiles) and spatially contiguous in WED
        # coordinates so all rendering paths observe the same page geometry.
        compat_page_size = 1024
        if new_tile > compat_page_size or compat_page_size % new_tile:
            raise SystemExit(
                f"{area}: --wed-regions-1024 requires a tile size that divides 1024px")
        tiles_per_side = compat_page_size // new_tile
        if tiles_per_side != 8:
            raise SystemExit(
                f"{area}: --wed-regions-1024 is an x2-only compatibility mode "
                f"(got {tiles_per_side} tiles per side)")

        canvases = {}
        page_index = 0
        placement = {}
        primary_region_count = 0
        for region_y in range(0, ov_h, tiles_per_side):
            for region_x in range(0, ov_w, tiles_per_side):
                canvas = Image.new("RGBA", (compat_page_size, compat_page_size), (0, 0, 0, 0))
                for dy in range(tiles_per_side):
                    row = region_y + dy
                    if row >= ov_h:
                        break
                    for dx in range(tiles_per_side):
                        col = region_x + dx
                        if col >= ov_w:
                            break
                        tile_id = cell_primary[row * ov_w + col]
                        if tile_id not in tiles or tile_id in placement:
                            continue
                        x, y = dx * new_tile, dy * new_tile
                        canvas.paste(tiles[tile_id], (x, y))
                        placement[tile_id] = (page_index, x, y)
                canvases[page_index] = canvas
                page_index += 1
                primary_region_count += 1

        # Door/secondary/animated tiles do not necessarily belong to the
        # base WED grid. Pack the remaining entries into ordinary 8x8 pages;
        # primary regions stay spatially stable and consume the first pages.
        remaining = sorted(idx for idx in tiles if idx not in placement)
        ancillary_page_count = 0
        for slot, tile_id in enumerate(remaining):
            local_page, within = divmod(slot, tiles_per_side * tiles_per_side)
            current_page = page_index + local_page
            if current_page not in canvases:
                canvases[current_page] = Image.new(
                    "RGBA", (compat_page_size, compat_page_size), (0, 0, 0, 0))
                ancillary_page_count += 1
            row, col = divmod(within, tiles_per_side)
            x, y = col * new_tile, row * new_tile
            canvases[current_page].paste(tiles[tile_id], (x, y))
            placement[tile_id] = (current_page, x, y)

        page_count = len(canvases)
        if page_count > 100:
            raise SystemExit(
                f"{area}: WED-aware 1024 layout needs {page_count} PVRZ pages; "
                "the EE TIS page namespace supports at most 100")
        print(f"WED-aware 1024 layout: {primary_region_count} primary regions + "
              f"{ancillary_page_count} ancillary pages = {page_count} pages")
    elif preserve_source_page_layout:
        canvases = {}
        for page in used_pages:
            source_w, source_h = page_size[page]
            canvas_size = (source_w * scale, source_h * scale)
            if canvas_size[0] > PAGE_SIZE or canvas_size[1] > PAGE_SIZE:
                raise SystemExit(
                    f"{area}: source page {page} would become {canvas_size[0]}x{canvas_size[1]}; "
                    f"page-layout preservation supports up to {PAGE_SIZE}px")
            canvases[page] = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        for idx, tile in tiles.items():
            page, u, v = entries[idx]
            x, y = u * scale, v * scale
            canvas = canvases[page]
            if x + new_tile > canvas.width or y + new_tile > canvas.height:
                raise SystemExit(f"{area}: tile {idx} exceeds preserved page {page}")
            canvas.paste(tile, (x, y))
            placement[idx] = (page, x, y)
        page_count = len(canvases)
        print(f"preserved {page_count} source PVRZ page layouts (no atlas border)")
    else:
        # The renderer samples exactly [u, u+128) with GL_LINEAR, so a tile whose
        # neighbour touches it in the atlas bleeds across the seam. Give every tile
        # a border of replicated edge pixels so the filter can only ever pick up the
        # tile's own colour.
        cell_px = new_tile + 2 * PAD
        # Le numero de page ne dispose que des caracteres que le prefixe laisse
        # libres : "A0900" (jour) en laisse 3, mais "A0900N" (nuit) seulement 2,
        # ce qui plafonne la variante nuit a 100 pages. Choisir la plus petite
        # page qui tienne dans ce budget plutot que d'emettre un resref trop long.
        max_pages = 10 ** (RESREF_MAX - len(prefix))
        sizes = [PAGE_SIZE] if PAGE_SIZE_ENV else [
            s for s in PAGE_SIZE_CANDIDATES if s >= PAGE_SIZE]
        page_px = per_row = per_page = None
        for candidate in sizes:
            row_count = candidate // cell_px
            if row_count == 0:
                continue
            page_px, per_row, per_page = candidate, row_count, row_count * row_count
            if -(-len(tiles) // per_page) <= max_pages:
                break
        if not per_row:
            raise SystemExit(
                f"{area}: padded tile of {cell_px}px does not fit any candidate page size")

        ordered = sorted(tiles)
        page_count = (len(ordered) + per_page - 1) // per_page
        if page_count > max_pages:
            raise SystemExit(
                f"{area}: {len(ordered)} tiles need {page_count} PVRZ pages of "
                f"{page_px}x{page_px}, but the prefix '{prefix}' ({len(prefix)} chars) "
                f"leaves only {RESREF_MAX - len(prefix)} digits for the page number, "
                f"capping this tileset at {max_pages} pages. Emitting more would "
                "produce a resref longer than 8 characters, which the engine cannot "
                "represent (CResRef is 8 bytes) and which crashes the game at render time.")
        canvases = []
        for slot, idx in enumerate(ordered):
            page, within = divmod(slot, per_page)
            row, col = divmod(within, per_row)
            while len(canvases) <= page:
                canvases.append(Image.new("RGBA", (page_px, page_px), (0, 0, 0, 0)))
            x = col * cell_px + PAD
            y = row * cell_px + PAD
            canvases[page].paste(tiles[idx], (x, y))
            placement[idx] = (page, x, y)

        # replicate edges into the padding
        for i, canvas in enumerate(canvases):
            arr = np.array(canvas)
            for idx, (page, x, y) in placement.items():
                if page != i:
                    continue
                block = arr[y - PAD:y + new_tile + PAD, x - PAD:x + new_tile + PAD]
                block[:PAD, PAD:-PAD] = block[PAD:PAD + 1, PAD:-PAD]
                block[-PAD:, PAD:-PAD] = block[-PAD - 1:-PAD, PAD:-PAD]
                block[:, :PAD] = block[:, PAD:PAD + 1]
                block[:, -PAD:] = block[:, -PAD - 1:-PAD]
            canvases[i] = Image.fromarray(arr)
        canvases = {i: c for i, c in enumerate(canvases)}
        print(f"repacked into {page_count} pages of {page_px}x{page_px} "
              f"({per_page} tiles/page, {PAD}px border, "
              f"cap {max_pages} for prefix '{prefix}')")

    new_entries = []
    for idx, (page, u, v) in enumerate(entries):
        if page == 0xFFFFFFFF and idx not in tiles:
            new_entries.append((0xFFFFFFFF, 0, 0))
        else:
            new_entries.append(placement[idx])

    # x4 opaque maps default to DXT1 to save space.  Any source alpha (water,
    # holes, silhouettes or feathered contours) forces DXT5: DXT1 cannot carry
    # it without changing the in-game geometry of the visible artwork.
    has_transparency = any(
        tile.getchannel("A").getextrema() != (255, 255) for tile in tiles.values()
    )
    if dxt1 and has_transparency:
        raise SystemExit(f"{area}: DXT1 interdit, le build contient de l'alpha")
    if scale == 4 and not has_transparency and not dxt1:
        dxt1 = True
        print("format: DXT1 automatique (x4 sans alpha)")
    elif dxt1:
        print("format: DXT1 demandé (aucun alpha)")
    else:
        print("format: DXT5 requis (alpha détecté)")
    page_fmt = {i: 7 if dxt1 else 11 for i in canvases}

    # --- encode PVRZ -----------------------------------------------------
    os.makedirs(out_dir, exist_ok=True)
    total = 0
    for page, canvas in canvases.items():
        pixel_format = "DXT1" if page_fmt[page] == 7 else "DXT5"
        buf = io.BytesIO()
        canvas.save(buf, format="DDS", pixel_format=pixel_format)
        dds = buf.getvalue()
        payload = dds[128:]

        w, h = canvas.size
        header = struct.pack("<13I", PVR_MAGIC, 0, page_fmt[page], 0, 0, 0, h, w, 1, 1, 1, 1, 0)
        pvr = header + payload
        blob = struct.pack("<I", len(pvr)) + zlib.compress(pvr, 9)

        path = os.path.join(out_dir, f"{prefix}{page:02d}.PVRZ".upper())
        with open(path, "wb") as fh:
            fh.write(blob)
        total += len(blob)
        print(f"  {os.path.basename(path)}: {w}x{h} -> {len(blob):,} bytes")

    # --- write TIS -------------------------------------------------------
    tis = bytearray()
    tis += b"TIS V1  "
    tis += struct.pack("<IIII", tile_count, 12, 24, new_tile)
    for page, u, v in new_entries:
        tis += struct.pack("<3I", page, u, v)
    tis_path = os.path.join(out_dir, f"{tileset_ref.upper()}.TIS")
    with open(tis_path, "wb") as fh:
        fh.write(tis)
    print(f"  {os.path.basename(tis_path)}: {tile_count} tiles, tile dimension {new_tile}, {len(tis):,} bytes")
    print(f"total PVRZ: {total/1024/1024:.1f} MB")


if __name__ == "__main__":
    args = sys.argv[1:]
    repair_water = "--transparent-full-water-base" in args
    soften_water = "--soften-water-contours" in args
    preserve_source_page_layout = "--preserve-source-page-layout" in args
    wed_regions_1024 = "--wed-regions-1024" in args
    dxt1 = "--dxt1" in args
    nearest_alpha = "--nearest-alpha" in args
    alpha_feather = 0.0
    feather = 0.0
    if "--water-contour-feather" in args:
        feather_index = args.index("--water-contour-feather")
        if feather_index + 1 >= len(args):
            raise SystemExit("--water-contour-feather requiert un rayon positif en pixels x1")
        try:
            feather = float(args[feather_index + 1])
        except ValueError as exc:
            raise SystemExit("--water-contour-feather requiert un nombre") from exc
        if feather <= 0:
            raise SystemExit("--water-contour-feather requiert un rayon positif")
        del args[feather_index:feather_index + 2]
        soften_water = True
    if "--alpha-contour-feather" in args:
        feather_index = args.index("--alpha-contour-feather")
        if feather_index + 1 >= len(args):
            raise SystemExit("--alpha-contour-feather requiert un rayon positif en pixels x1")
        try:
            alpha_feather = float(args[feather_index + 1])
        except ValueError as exc:
            raise SystemExit("--alpha-contour-feather requiert un nombre") from exc
        if alpha_feather <= 0:
            raise SystemExit("--alpha-contour-feather requiert un rayon positif")
        del args[feather_index:feather_index + 2]
    args = [arg for arg in args if arg not in (
        "--transparent-full-water-base", "--soften-water-contours", "--preserve-source-page-layout",
        "--wed-regions-1024", "--dxt1", "--nearest-alpha", "--alpha-contour-feather")]
    if len(args) not in (3, 4):
        raise SystemExit(
            "Usage: build_upscaled_area.py AREA PRIMARY.png OUT_DIR "
            "[SECONDARY.png] [--transparent-full-water-base] [--soften-water-contours] "
            "[--water-contour-feather <rayon-x1>] [--preserve-source-page-layout] "
            "[--wed-regions-1024] [--dxt1] [--nearest-alpha] [--alpha-contour-feather <rayon-x1>]"
        )
    build(args[0], args[1], args[2], args[3] if len(args) == 4 else None,
          transparent_full_water_base=repair_water, soften_water_contours=soften_water,
          water_contour_feather=feather,
          preserve_source_page_layout=preserve_source_page_layout,
          wed_regions_1024=wed_regions_1024,
          dxt1=dxt1,
          soften_all_alpha_contours=not nearest_alpha,
          alpha_contour_feather=alpha_feather)
