"""Use analysed v6 world contours without duplicating AR0516 runtime frames."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
source=ROOT/'pipeline/recipes/planar-sphinct-wed-crisp-20261010-v6/build.py'
text=source.read_text(encoding='utf-8').replace("TAG='planar-sphinct-wed-crisp-20261010-v6'","TAG='planar-sphinct-wed-crisp-20261010-v7'")
text=text.replace("GAME=get_path('bg2ee_game_root');report=v2.load_json(OUT/'analysis-all-phases.json');assert not RUN.exists() and not PACK.exists()",
 "GAME=get_path('bg2ee_game_root');OUT.mkdir(parents=True,exist_ok=True);report=v2.load_json(ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v6/analysis-all-phases.json');assert not RUN.exists() and not PACK.exists()")
text=text.replace("if area=='AR0517':\n  areas.append", "if area=='AR0516':\n  areas.append(dict(area=area,status='renderer-world-masks',base=info['base'],before_payload=payload(base),target_positions=[c['position'] for c in area_checks]));continue\n if area=='AR0517':\n  areas.append")
text=text.replace('Prepared AR0516 3 bound variants + AR0518-21 4 cells','Prepared AR0516 3 renderer masks + AR0518-21 4 cells')
generated=Path(__file__).with_name('build.py');assert not generated.exists();generated.write_text(text,encoding='utf-8')
print(generated)
