"""Record the installed available Large16 lot; keep source inventory and QA separate."""
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
REF = RUN.relative_to(ROOT).as_posix()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


installation = read(RUN / "installation-verification.json")
receipt = read(RUN / "ingame-installation/active-test.json")
generation = read(RUN / "current-generation.json")
production = read(RUN / "production.json")
assert installation["status"] == receipt["status"] == "installed-pending-ingame-qa"
assert installation["resources"] == 20 and installation["frames"] == 1692
assert not installation["SDF"] and not installation["ingame_QA"]
assert sha(RUN / "ingame-installation/active-test.json").upper() == installation["installation_receipt_sha256"]
config = read(ROOT / "config/workspace-paths.local.json")
game = Path(config["paths"]["bg2ee_game_root"])
assert sha(game / receipt["catalog_relative"]) == generation["catalog"]["sha256"]
for leaf in receipt["new_shards"]:
    assert sha(game / leaf["registry"]) == leaf["sha256"].lower()
for item in receipt["preserved_files"]:
    assert sha(game / item["relative_path"]).lower() == item["sha256"].lower()
assert sha(game / receipt["fixture"]["target"]) == receipt["fixture"]["sha256"]

record = {
    "reference": f"{REF}/current-generation.json",
    "selection": f"{REF}/selection.json",
    "animation_ids": generation["animation_ids"],
    "source_absent_animation_ids": generation["source_absent_animation_ids"],
    "native_kind": 0,
    "owner": 11,
    "bams": sorted({r for w in production["plan"]["witnesses"] for r in w["refs"]}),
    "original_world_bams": 12,
    "auxiliary_inventory_bams": 1,
    "original_BAM_frames": 1114,
    "resources": 20,
    "physical_frames": 1692,
    "logical_frame_occurrences": 1692,
    "unique_original_BAM_source_work": 1053,
    "unique_source_work": 1567,
    "unique_encoded_work": 1570,
    "encoded_cache_hits": 176,
    "new_encoded_work": 1388,
    "special_work_without_GPU": 6,
    "new_neural_targets": 8328,
    "resume_cache_hits": 1570,
    "native_replacement_palettes": {"0xA200": "MWYV_WS"},
    "excluded_shared_Quadrant_BAMs": production["plan"]["witnesses"][0]["excluded_non_native_refs"],
    "native_scope_reference": f"{REF}/native-scope.json",
    "scope": "complete available native Large16 world; all six banks/directions; INV auxiliary without UI claim; two declared source-absent IDs excluded",
    "registry_version": 7,
    "scale": 2,
    "SDF": False,
    "world_filter": "CatmullRom",
    "installation_reference": f"{REF}/ingame-installation/active-test.json",
    "installation_snapshot": f"{REF}/installation-verification.json",
    "state": "family-complete-available-produced-installed-ingame-QA-pending",
    "qa_ingame": False,
    "release": False,
}
path = ROOT / "sprite/index/q3m-work-tracking.json"
tracking = read(path)
assert not any(p["family"] == "monster_large16" for p in tracking["current_recipe_complete_productions"])
tracking["current_recipe_complete_productions"].append({"family": "monster_large16", **record})
family = next(f for f in tracking["families"] if f["engine_section"] == "monster_large16")
family["current_full_production"] = record
family["source_dedup"]["remaining_gpu_work"] = 0
family["source_dedup"]["remaining_gpu_work_scope"] = "current available native Large16 selection; shared Quadrant prefix assets excluded"
family["current_colour_witness"]["state"] = "host-verified-complete-family-installed-ingame-pending"
totals = tracking["queue_totals"]
assert [totals[k] for k in ["current_recipe_complete_families", "current_recipe_complete_animation_ids", "current_recipe_installed_animation_ids"]] == [3, 7, 7]
totals.update(current_recipe_complete_families=4, current_recipe_complete_animation_ids=10, current_recipe_installed_animation_ids=10)
for key in ["installed_candidate_reference", "latest_installation_verification_reference"]:
    tracking["engine_integration"][key] = f"{REF}/installation-verification.json"
tracking["colour_variants"]["state"] = "Q3m-x2-flying-accepted-Ankheg-V9-SDF-stable-accepted-Ogre-installed-Large16-V7-no-SDF-installed-QA-pending-other-families-pilot"
path.write_text(json.dumps(tracking, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Preserve every unrelated CSV line, including its original newline style.
path = ROOT / "sprite/index/q3m-work-items.csv"
lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
fields = next(csv.reader([lines[0]]))
changed = set()
for i, line in enumerate(lines[1:], 1):
    row = dict(zip(fields, next(csv.reader([line]))))
    aid = row["animation_id"]
    if aid not in generation["animation_ids"]:
        continue
    row["queue_state"] = "current-recipe-complete-installed-QA-pending"
    row["q3m_final_work_count_known"] = str(next(w["encoded_work"] for w in production["plan"]["witnesses"] if w["animation_id"] == aid))
    row["q3m_v7_full_production_reference"] = record["reference"]
    row["q3m_v7_installation_reference"] = record["installation_reference"]
    row["colour_variant_state"] = "v7-full-native-Large16-x2-no-SDF-installed-QA-pending" + ("-native-MWYV_WS-palette" if aid == "0xA200" else "")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\r\n" if line.endswith("\r\n") else "\n")
    writer.writerow([row[k] for k in fields])
    lines[i] = stream.getvalue()
    changed.add(aid)
assert changed == set(generation["animation_ids"])
path.write_bytes("".join(lines).encode("utf-8"))

path = ROOT / "sprite/SUIVI_Q3M.md"
text = path.read_text(encoding="utf-8")
needle = "- Essai Spline Fit 1 Ankheg"
new = f"- Quatrième famille complète disponible : **`monster_large16` / trois IDs A000/A100/A200 / deux modèles, trois contrats couleur / V7 x2 sans SDF**, produite et installée ; **QA ingame en attente**. Source native : 12 BAM monde + un INV auxiliaire / 1 114 frames originales ; 20 feuilles / 1 692 frames avec palette blanche native `MWYV_WS`. A201/A202 sans BAM déclarés ; douze BAM partagés Quadrant hors appels Large16 exclus. `../{REF}/README.md`.\n"
assert needle in text
text = text.replace(needle, new + needle, 1)
text = text.replace("| `monster_large16` | 3/5 | — | Profil grands monstres à 16 directions ; wyvernes, charognards rampants. |", "| `monster_large16` | 3/5 | — | Wyverne, charognard rampant, wyverne blanche ; **famille disponible complète V7 x2 sans SDF installée**, 20 feuilles / 1 692 frames, palette blanche native ; QA ingame en attente. Deux IDs sans BAM. |")
text = text.replace("7 IDs / 3 familles complètes installées", "10 IDs / 4 familles disponibles complètes installées")
needle = "- Coût du reste des 335 animations"
text = text.replace(needle, f"- Large16 complet disponible : **1 114 frames BAM originales → 1 053 sources**, avec palette blanche native **1 567 sources couleur / 1 570 contrats = 176 hits acquis + 1 388 nouveaux encodages + six spéciaux sans GPU** ; 8 328 nouvelles cibles. Reprise 1 570/1 570 hits sans Torch. Douze BAM Quadrant partagés exclus ; `../{REF}/production.json`.\n" + needle, 1)
text = text.replace("| Character CHFB1 SDF en réserve |", "| Large16 complet sans SDF | `q3m-monster-large16-full-x2-20261004-v1/` ; natif owner11, trois IDs disponibles, 20 feuilles / 1 692 frames ; palette blanche réelle, installé, QA en attente | non committé |\n| Character CHFB1 SDF en réserve |", 1)
text = text.replace('C:CreateCreature("ANKHEG01")\n```', 'C:CreateCreature("ANKHEG01")\nC:CreateCreature("WYVBAB01")\nC:CreateCreature("CARCRA01")\nC:CreateCreature("QMWYVW01") -- témoin blanc ajouté, même CRE source sauf ID animation A200\n```', 1)
text = text.replace("catalogue `56be42fb…fcc8`, trois shaders", f"catalogue enrichi Large16 **`6fbb2f02…44c80`**, trois shaders", 1)
text = text.replace("Catalogue parent exact ⇒ CHFB1 V6 actif", "Catalogue parent de la restauration Character historiquement exact ; routes Character préservées dans le nouveau catalogue Large16 ⇒ CHFB1 V6 actif", 1)
text += f"\n- Installation Large16 actuelle : `../{REF}/installation-verification.json` ; 20 nouvelles feuilles V7 sans SDF + CRE témoin blanc, **99 fichiers préservés**, 88 IDs/50 253 routes hérités identiques ; catalogue actif 91 IDs/4 592 ressources. QA antérieures inchangées ; Large16 en attente utilisateur.\n"
path.write_text(text, encoding="utf-8")

path = ROOT / "sprite/index/README.md"
with path.open("a", encoding="utf-8") as out:
    out.write(f"\n## Large16 Q3m x2 sans SDF — 2026-10-04\n\n- `q3m-work-tracking.json`, `../SUIVI_Q3M.md` : quatrième famille disponible complète installée, dix IDs complets ; QA acquises toujours deux familles/six IDs.\n- `../../{REF}/README.md` : trois IDs, deux modèles/trois palettes, scope natif 12 BAM monde + INV auxiliaire ; vingt feuilles / 1 692 frames. Les 25 BAM de l'inventaire par préfixe restent une donnée source, douze quadrants hors appels Large16. A201/A202 explicitement sans source.\n- Production/installation prouvées séparément ; QA ingame en attente ; Character SDF en stock, Ankheg stable conservé.\n")

path = ROOT / "pipeline/PALETTE_Q3M_V7.md"
with path.open("a", encoding="utf-8") as out:
    out.write(f"\n## Large16 : scope et palettes fixes — 2026-10-04\n\n- Cas `../{REF}/README.md` : native owner11, cellules G1/G2/G3 + E ; préfixe MWYV inclut aussi douze BAM Quadrant inutilisés par Large16. Une famille disponible complète peut déclarer ses IDs sans source, exactement selon l'inventaire ; ne pas produire des quadrants/frames 0×0 hors appels natifs pour satisfaire un compteur de préfixe.\n- `general.new_palette` remplace réellement la palette BAM fixe : A200 utilise BMP-P8 `MWYV_WS` (SHA dans sélection), avant guides/cibles/fitting/clés/source-palette guard. Couleurs natives distinctes = contrats distincts ; RGB/indices identiques compatibles restent dédupliqués. `q3m_family_witnesses.py` exige cet override explicite pour une famille complète ; pilote historique partiel préservé.\n- NativeFixed index1 peut avoir RGB non noir ; tint natif aussi appliqué à son RGB sous flag 0x20000. Ajustement de l'attente scalaire locale, comparaison Unicorn épinglée sur les 256 entrées K6 ; producteurs/preuves historiques non réécrits. V7 ordinary conserve cette ombre native.\n- Vérifié : dix tests hôte, sondes native isolée/combinée 20 ressources/1 692 frames × six palettes × trois formats, reprise 1 570 hits sans Torch. Aucun SDF nouveau ni moteur recompilé.\n")
print(json.dumps({"installed_verified": True, "new_leaves": 20, "preserved_files": len(receipt["preserved_files"]), "family_complete_count": 4, "complete_IDs": 10, "ingame_QA": False}))
