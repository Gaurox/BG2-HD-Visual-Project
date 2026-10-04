"""Record explicit user acceptance of the installed V7 lot, separately from SDF."""
import csv, hashlib, io, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
REF = RUN.relative_to(ROOT).as_posix()
QA = "sprite/index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json"

def read(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def identity(p): return dict(path=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest(), bytes=p.stat().st_size)

assert not (ROOT / QA).exists()
generation = read(RUN / "current-generation.json")
receipt = read(RUN / "ingame-installation/active-test.json")
assert receipt["status"] == "installed-pending-ingame-qa"
game = Path(read(ROOT / "config/workspace-paths.local.json")["paths"]["bg2ee_game_root"])
assert hashlib.sha256((game / receipt["catalog_relative"]).read_bytes()).hexdigest() == receipt["catalog_sha256"]
qa = dict(schema="bg2-upscale-native-sprite-family-qa-decision-v1", status="accepted", qa_state="passed", recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    scope=dict(kind="installed-complete-available-native-family", engine_family="monster_large16", animation_ids=generation["animation_ids"], source_absent_animation_ids=generation["source_absent_animation_ids"], variant_id="q3m-v7-k6-four-partners-eight-levels-x2-catmullrom-no-SDF", scale=2, resources=20, frames=1692, original_world_BAMs=12, auxiliary_inventory_BAMs=1, UI_integration_claimed=False),
    visual_qa=dict(result="pass", authority="user", user_statement="c'est propre ! met a jour le suivi puis commite. ensuite tente SDF sur les 3 et installe ingame", scenario="user acceptance of the installed three available Large16 variants after CLUA handoff", individual_scenario_details="not specified by user", test_commands_provided=["WYVBAB01", "CARCRA01", "QMWYVW01"]),
    runtime_contract=dict(runtime=generation["runtime"], dll=generation["dll"], ini_sha256=receipt["ini_sha256"], catalogue_sha256=receipt["catalog_sha256"], owner=11, native_palette_kind=0, class_profile_id=8, decode_rule_id=3, palette="live-native; A200 MWYV_WS", world_filter="CatmullRom", SDF=False, native_geometry=True),
    provenance={name:identity(RUN / path) for name,path in [("selected_generation","current-generation.json"),("production","production.json"),("local_verification","verification.json"),("installation_snapshot","installation-verification.json"),("installed_receipt","ingame-installation/active-test.json")]}, resources=receipt["new_shards"], release_state="not-promoted")
(ROOT / QA).parent.mkdir(parents=True, exist_ok=True)
(ROOT / QA).write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
path = ROOT / "sprite/index/q3m-work-tracking.json"
d = read(path)
family = next(f for f in d["families"] if f["engine_section"] == "monster_large16")
for record in [family["current_full_production"],next(p for p in d["current_recipe_complete_productions"] if p["family"] == "monster_large16")]:
    record.update(state="family-complete-available-produced-installed-ingame-accepted",qa_ingame=True,qa_reference=QA)
family["current_colour_witness"].update(state="ingame-accepted-via-complete-available-family",qa_reference=QA)
d["queue_totals"].update(current_recipe_ingame_accepted_families=3,current_recipe_ingame_accepted_animation_ids=9)
d["colour_variants"]["state"] = d["colour_variants"]["state"].replace("Large16-V7-no-SDF-installed-QA-pending", "Large16-V7-no-SDF-accepted")
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
path = ROOT / "sprite/index/q3m-work-items.csv"
lines = path.read_bytes().decode().splitlines(keepends=True); fields=next(csv.reader([lines[0]]))
for i,line in enumerate(lines[1:],1):
    row=dict(zip(fields,next(csv.reader([line]))))
    if row["animation_id"] not in generation["animation_ids"]:continue
    row["queue_state"]="current-recipe-complete-installed-ingame-accepted"
    row["colour_variant_state"]=row["colour_variant_state"].replace("installed-QA-pending","installed-ingame-accepted")
    out=io.StringIO(newline="");csv.writer(out,lineterminator="\r\n" if line.endswith("\r\n") else "\n").writerow([row[k] for k in fields]);lines[i]=out.getvalue()
path.write_bytes("".join(lines).encode())
path=ROOT / "sprite/SUIVI_Q3M.md";text=path.read_text(encoding="utf-8")
text=text.replace("produite et installée ; **QA ingame en attente**. Source native", "produite, installée et **validée ingame par l'utilisateur**. Source native")
text=text.replace("palette blanche native ; QA ingame en attente. Deux IDs sans BAM.", "palette blanche native ; **validée ingame**. Deux IDs sans BAM.")
text=text.replace("6 IDs / 2 familles validées (`flying`, `monster_ankheg` V9 stable)", "9 IDs / 3 familles validées (`flying`, `monster_ankheg` V9 stable, `monster_large16` V7 sans SDF)")
text=text.replace("palette blanche réelle, installé, QA en attente | non committé", "palette blanche réelle, installé, validé ingame | commit du lot Large16")
text=text.replace("QA antérieures inchangées ; Large16 en attente utilisateur.", f"QA V7 Large16 acceptée : `index/qa-decisions/monster_large16/{Path(QA).name}` ; un essai SDF conserve une QA distincte.")
path.write_text(text,encoding="utf-8")
for p in [RUN / "README.md",ROOT / "sprite/index/README.md"]:
    with p.open("a",encoding="utf-8") as out:out.write(f"\n- 2026-10-04 : **V7 sans SDF validé ingame**, utilisateur « c'est propre ! » ; QA immuable `{QA}`. Trois familles/neuf IDs acceptés. Les mentions en attente ci-dessus décrivent la remise initiale ; futur SDF = autre variante, QA distincte.\n")
print(QA)
