"""Resolve canonical sprite-family workspaces from normalized inventory rows."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAMILIES_ROOT = PROJECT_ROOT / "sprite" / "families"
GROUPS_PATH = PROJECT_ROOT / "sprite" / "index" / "family-groups.csv"
GROUP_FIELDS = (
    "engine_section",
    "macro_group",
    "directory",
    "layout_kind",
    "bucket_policy",
)
LAYOUT_KINDS = {"character-components", "single-family"}
BUCKET_POLICIES = {"none", "high-byte", "named-high-byte"}
RESREF_RE = re.compile(r"[A-Z0-9_]{1,8}")
ANIMATION_ID_RE = re.compile(r"0x[0-9A-Fa-f]{4}")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

MONSTER_ICEWIND_BUCKETS = {
    "E0": "e0xx-classic-monsters",
    "E2": "e2xx-iwd-mixed-creatures",
    "E3": "e3xx-ghouls-and-ghosts",
    "E4": "e4xx-goblins",
    "E5": "e5xx-lizardfolk",
    "E6": "e6xx-myconids",
    "E7": "e7xx-orogs",
    "E8": "e8xx-orcs",
    "E9": "e9xx-salamanders",
    "EA": "eaxx-shriekers-and-shadows",
    "EB": "ebxx-skeletons",
    "EC": "ecxx-wights",
    "ED": "edxx-yuan-ti",
    "EE": "eexx-zombies",
    "EF": "efxx-water-weird",
}


@dataclass(frozen=True)
class GroupRule:
    engine_section: str
    macro_group: str
    directory: PurePosixPath
    layout_kind: str
    bucket_policy: str


def slug(value: str) -> str:
    result = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not result or not SLUG_RE.fullmatch(result):
        raise ValueError(f"valeur impossible à convertir en slug: {value!r}")
    return result


def normalized_animation_id(value: str) -> str:
    if not ANIMATION_ID_RE.fullmatch(value):
        raise ValueError(f"animation_id invalide: {value!r}")
    return f"0x{int(value, 16):04X}"


def _safe_directory(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"directory non canonique: {value!r}")
    if any(not SLUG_RE.fullmatch(part) for part in path.parts):
        raise ValueError(f"directory non kebab-case: {value!r}")
    return path


def load_group_rules(path: Path = GROUPS_PATH) -> dict[str, GroupRule]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != GROUP_FIELDS:
            raise ValueError(
                f"schéma inattendu: {path}; attendu: {','.join(GROUP_FIELDS)}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError(f"table de groupes vide: {path}")
    result: dict[str, GroupRule] = {}
    for row in rows:
        section = row["engine_section"].strip()
        macro = row["macro_group"].strip()
        layout = row["layout_kind"].strip()
        bucket = row["bucket_policy"].strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", section):
            raise ValueError(f"engine_section invalide: {section!r}")
        if section in result:
            raise ValueError(f"engine_section dupliqué: {section}")
        if not SLUG_RE.fullmatch(macro):
            raise ValueError(f"macro_group invalide: {macro!r}")
        if layout not in LAYOUT_KINDS:
            raise ValueError(f"layout_kind invalide pour {section}: {layout!r}")
        if bucket not in BUCKET_POLICIES:
            raise ValueError(f"bucket_policy invalide pour {section}: {bucket!r}")
        if layout == "character-components" and bucket != "none":
            raise ValueError(f"layout Character incompatible avec bucket {bucket!r}")
        if layout == "single-family" and bucket == "none":
            raise ValueError(f"layout mono-famille sans bucket: {section}")
        result[section] = GroupRule(
            engine_section=section,
            macro_group=macro,
            directory=_safe_directory(row["directory"].strip()),
            layout_kind=layout,
            bucket_policy=bucket,
        )
    return result


def split_values(value: str) -> tuple[str, ...]:
    return tuple(sorted({part.strip().upper() for part in value.split(";") if part.strip()}))


def character_type_slug(animation: Mapping[str, str]) -> str:
    ordered = (
        animation.get("symbol_race", ""),
        animation.get("symbol_gender", ""),
        animation.get("symbol_class", ""),
        animation.get("symbol_variant", ""),
    )
    values = [slug(value) for value in ordered if value.strip()]
    return "-".join(values) if values else slug(animation.get("ids_symbol", ""))


def character_component_slug(family: Mapping[str, str]) -> str:
    prefix = family.get("bam_prefix", "").upper()
    if not RESREF_RE.fullmatch(prefix):
        raise ValueError(f"bam_prefix invalide: {prefix!r}")
    if family.get("layer_kind", "").lower() == "body":
        return prefix.lower()
    items = split_values(family.get("item_resrefs", ""))
    if items:
        return f"{items[0].lower()}-{prefix.lower()}"
    layer = slug(family.get("layer_kind", ""))
    variant = slug(family.get("variant_value", ""))
    return f"{layer}-{variant}-{prefix.lower()}"


def _bucket(rule: GroupRule, animation_id: str) -> str:
    high_byte = animation_id[2:4].upper()
    if rule.bucket_policy == "named-high-byte":
        value = MONSTER_ICEWIND_BUCKETS.get(high_byte)
        if value is None:
            raise ValueError(f"bucket MonsterIcewind absent pour 0x{high_byte}xx")
        return value
    if rule.bucket_policy == "high-byte":
        return f"{high_byte.lower()}xx"
    raise ValueError(f"bucket non applicable pour {rule.engine_section}")


def family_directory(
    family: Mapping[str, str],
    animation: Mapping[str, str],
    *,
    rules: Mapping[str, GroupRule] | None = None,
    project_root: Path = PROJECT_ROOT,
) -> Path:
    active_rules = dict(rules or load_group_rules())
    section = family.get("engine_section", "").strip()
    rule = active_rules.get(section)
    if rule is None:
        raise ValueError(f"aucune règle de rangement pour engine_section={section!r}")
    animation_id = normalized_animation_id(family.get("animation_id", ""))
    prefix = family.get("bam_prefix", "").upper()
    if not RESREF_RE.fullmatch(prefix):
        raise ValueError(f"bam_prefix invalide: {prefix!r}")
    base = project_root / "sprite" / "families" / Path(*rule.directory.parts)
    if rule.layout_kind == "character-components":
        root = base / f"{animation_id[2:].lower()}-{character_type_slug(animation)}"
        return root / character_component_slug(family)
    label = slug(family.get("ids_symbol", ""))
    return base / _bucket(rule, animation_id) / (
        f"{animation_id[2:].lower()}-{prefix.lower()}-{label}"
    )


def project_relative(path: Path, project_root: Path = PROJECT_ROOT) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as error:
        raise ValueError(f"chemin hors workspace: {path}") from error
