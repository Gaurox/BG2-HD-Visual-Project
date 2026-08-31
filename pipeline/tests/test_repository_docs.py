from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_DOCS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "docs" / "DECISIONS.md",
    ROOT / "docs" / "ASSET_TRACKING_CONTRACT.md",
    ROOT / "docs" / "GLOBAL_ASSET_REGISTRY.md",
    ROOT / "docs" / "GRAPHICS_INVENTORY.md",
    ROOT / "docs" / "WORKSPACE_INTEGRITY.md",
    ROOT / "docs" / "WORKFLOW_PERFORMANCE_AUDIT.md",
    ROOT / "pipeline" / "README.md",
    ROOT / "pipeline" / "PROBLEMES_A_RESOUDRE.md",
    ROOT / "pipeline" / "scripts" / "README.md",
    ROOT / "animations" / "README.md",
    ROOT / "sprite" / "README.md",
    ROOT / "sprite" / "FAMILY_APPEND.md",
    ROOT / "interface" / "README.md",
    ROOT / "interface" / "menus-options-bg2ee" / "README.md",
    ROOT / "interface" / "menus-options-bg2ee" / "docs" / "MENU_UPSCALE.md",
    ROOT / "portraits" / "README.md",
    ROOT / "maps" / "technical-overlays" / "README.md",
    ROOT
    / "engine"
    / "InfinityEngine-Enhancer"
    / "source-patchee"
    / "README.md",
    ROOT
    / "engine"
    / "InfinityEngine-Enhancer"
    / "source-patchee"
    / "AGENTS.md",
    ROOT / "releases" / "BG2-HD-Upscale" / "README.md",
)
AI_FIRST_DOCS = (
    ROOT / "AGENTS.md",
    ROOT / "README.md",
    ROOT / "pipeline" / "README.md",
    ROOT / "animations" / "README.md",
    ROOT / "sprite" / "README.md",
    ROOT / "interface" / "README.md",
    ROOT / "engine" / "InfinityEngine-Enhancer" / "source-patchee" / "AGENTS.md",
    ROOT / "engine" / "InfinityEngine-Enhancer" / "source-patchee" / "README.md",
    ROOT / "releases" / "BG2-HD-Upscale" / "README.md",
    ROOT
    / "releases"
    / "BG2-HD-Upscale"
    / "docs"
    / "INSTALLER_AND_UPSCALE_WORKFLOW.md",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
NON_OPERATIONAL_PARTS = {
    "archive",
    "backups",
    "proto",
    "runs",
    "temp",
    "tmp",
    "_rollback",
}


def local_links(path: Path) -> list[tuple[str, Path]]:
    links: list[tuple[str, Path]] = []
    content = path.read_text(encoding="utf-8-sig")
    for raw_target in LINK_RE.findall(content):
        target = raw_target.strip().strip("<>").split("#", 1)[0]
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            continue
        resolved = (path.parent / unquote(target)).resolve()
        links.append((raw_target, resolved))
    return links


class RepositoryDocumentationTests(unittest.TestCase):
    def test_canonical_documents_exist(self) -> None:
        for path in CANONICAL_DOCS:
            self.assertTrue(path.is_file(), f"missing canonical document: {path}")

    def test_canonical_relative_links_exist(self) -> None:
        failures: list[str] = []
        for path in CANONICAL_DOCS:
            for raw_target, target in local_links(path):
                if not target.exists():
                    failures.append(f"{path.relative_to(ROOT)} -> {raw_target}")
        self.assertEqual(failures, [], "broken canonical links:\n" + "\n".join(failures))

    def test_ai_first_rule_is_visible_from_main_entry_points(self) -> None:
        markers = (
            "Règle documentaire : écrire pour des agents IA",
            "Toute nouvelle documentation ou modification doit privilégier la densité d’information",
            "Éviter la prose longue",
        )
        for path in AI_FIRST_DOCS:
            content = path.read_text(encoding="utf-8-sig")
            for marker in markers:
                self.assertIn(marker, content, f"missing AI-first rule in {path}")

    def test_entry_points_do_not_route_operations_into_data_or_archives(self) -> None:
        failures: list[str] = []
        for path in CANONICAL_DOCS:
            for raw_target, target in local_links(path):
                try:
                    relative = target.relative_to(ROOT)
                except ValueError:
                    continue
                if NON_OPERATIONAL_PARTS.intersection(relative.parts):
                    failures.append(f"{path.relative_to(ROOT)} -> {raw_target}")
        self.assertEqual(
            failures,
            [],
            "canonical docs must not route operations into data/archive paths:\n"
            + "\n".join(failures),
        )

    def test_root_router_names_every_core_domain(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8-sig")
        for marker in (
            "pipeline/README.md",
            "animations/README.md",
            "sprite/README.md",
            "interface/README.md",
            "INSTALLER_AND_UPSCALE_WORKFLOW.md",
            "docs/DECISIONS.md",
        ):
            self.assertIn(marker, readme)

    def test_agent_entrypoint_covers_workspace_contract(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8-sig")
        for marker in (
            "## Sources de vérité",
            "## Projections générées",
            "source",
            "production",
            "QA",
            "installation",
            "release",
            "registry.json",
            "runs.json",
            "config://",
            "test_changed.py --targeted",
            "workspace.py refresh --changed",
            "--run",
            "Ne jamais réécrire un run",
        ):
            self.assertIn(marker, agents)

    def test_three_new_agent_routes_are_explicit(self) -> None:
        scenarios = {
            ROOT / "sprite" / "README.md": (
                "## Sources de vérité",
                "## Méthode actuelle",
                "XBR2X_RASTER_CONTRACT.md",
                "archive/legacy/sprite-docs/",
                "## Tests légers",
            ),
            ROOT / "pipeline" / "README.md": (
                "areas.csv",
                "run_seedvr_comfyui.py",
                "anciens splitters manuels sont archivés",
                "## Tests légers",
            ),
            ROOT
            / "releases"
            / "BG2-HD-Upscale"
            / "docs"
            / "INSTALLER_AND_UPSCALE_WORKFLOW.md": (
                "## Source of truth",
                "explicit affirmative answer",
                "Test-BG2HD-Phase2.ps1",
                "release_status",
            ),
        }
        for path, markers in scenarios.items():
            content = path.read_text(encoding="utf-8-sig")
            for marker in markers:
                self.assertIn(marker, content, f"{path} must reference {marker}")

    def test_specialized_active_domains_are_routed(self) -> None:
        portraits = (ROOT / "portraits" / "README.md").read_text(encoding="utf-8-sig")
        for marker in (
            "inventaire_portraits.csv",
            "extract_joinable_portraits.py",
            "organize_ppe_portraits.py",
        ):
            self.assertIn(marker, portraits)
        overlays = (ROOT / "maps" / "technical-overlays" / "README.md").read_text(
            encoding="utf-8-sig"
        )
        for marker in (
            "overlay-sources.json",
            "extract_legacy_tis_frames.py",
            "build_upscaled_legacy_tis.py",
        ):
            self.assertIn(marker, overlays)


if __name__ == "__main__":
    unittest.main()
