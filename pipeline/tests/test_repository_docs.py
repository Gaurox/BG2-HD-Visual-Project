from __future__ import annotations

import re
import unittest
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
ENTRY_DOCS = (
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "docs" / "PRODUCTION_RAPIDE.md",
    ROOT / "pipeline" / "README.md",
    ROOT / "animations" / "README.md",
    ROOT / "sprite" / "README.md",
    ROOT / "releases" / "BG2-HD-Upscale" / "README.md",
)
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def local_links(path: Path) -> list[tuple[str, Path]]:
    links = []
    for raw in LINK_RE.findall(path.read_text(encoding="utf-8-sig")):
        target = raw.strip().strip("<>").split("#", 1)[0]
        if target and "://" not in target and not target.startswith(("mailto:", "#")):
            links.append((raw, (path.parent / unquote(target)).resolve()))
    return links


class RepositoryDocumentationTests(unittest.TestCase):
    def test_entry_documents_and_links_exist(self) -> None:
        failures = []
        for path in ENTRY_DOCS:
            if not path.is_file():
                failures.append(f"missing: {path.relative_to(ROOT)}")
                continue
            for raw, target in local_links(path):
                if not target.exists():
                    failures.append(f"{path.relative_to(ROOT)} -> {raw}")
        self.assertEqual([], failures, "broken documentation:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
