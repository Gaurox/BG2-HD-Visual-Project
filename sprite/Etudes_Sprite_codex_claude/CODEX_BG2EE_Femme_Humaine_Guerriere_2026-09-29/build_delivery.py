"""Assemble the independent Codex desktop guide inside the permitted workspace."""
from pathlib import Path
import csv,gzip,hashlib,json,re,shutil

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'delivery'/'CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29'
DEST.mkdir(parents=True,exist_ok=True)
main_files=[
 'GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md','GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.html',
 'engine_research.md','engine_research.html','inventory_research.md','inventory_research.html',
 'upscale_research.md','upscale_research.html','engine_disassembly_codex.txt',
 'assets_inventory.csv','assets_inventory_items.csv','assets_inventory_shared_slots.json',
 'assets_inventory.json.gz','CODEX_inventory_annexes.zip','inspect_engine_codex.py',
 'fetch_engine_sources_codex.py','render_guide.mjs','build_delivery.py',
]
for file in main_files:
 shutil.copy2(ROOT/file,DEST/file)
for folder in ['upscale','palette','inventory_tools','source_reference','sources_inventory']:
 shutil.copytree(ROOT/folder,DEST/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
# Only final-inventory BAMs: exclude exploratory WPL extractions.
native=DEST/'vanilla_inventory';native.mkdir(exist_ok=True)
with (ROOT/'assets_inventory.csv').open(encoding='utf-8-sig',newline='') as f:
 for row in csv.DictReader(f):
  name=row['resref']+'.BAM'
  shutil.copy2(ROOT/'vanilla_inventory'/name,native/name)
for file in (ROOT/'vanilla_inventory').iterdir():
 if file.is_file() and file.suffix.upper()!='.BAM':shutil.copy2(file,native/file.name)
(DEST/'LIRE_D_ABORD_CODEX.txt').write_text(
 'CODEX — recherche indépendante BG2EE, humaine guerrière HD, 29 septembre 2026.\n\n'
 'Ouvrir GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.html dans un navigateur.\n'
 'La version Markdown est également fournie. Aucune connexion nécessaire pour le guide et ses visuels.\n'
 'Cliquer sur une image pour son affichage intégral. Les WEBP sont animés.\n\n'
 'Inventaire : assets_inventory.csv (774 BAM) ; assets_inventory_items.csv (870 ITM).\n'
 'Données intégrales : assets_inventory.json.gz ou CODEX_inventory_annexes.zip.\n'
 'Scripts : exemples à relancer dans une nouvelle version d’étude depuis le dépôt/config local ;\n'
 'les chemins des runtimes et du dépôt doivent être adaptés après déplacement.\n'
 'Capstone/pefile pour le désassemblage restent dans le dossier de recherche du projet.\n\n'
 'Aucun audit Claude Code lu. Aucun fichier installé ou release modifié.\n'
 'Les aperçus sont des simulations hors jeu ; aucune acceptation ingame revendiquée.\n',encoding='utf-8')
# Verify referenced local links and images in primary Markdown/HTML, without networking.
missing=[];references=[]
for filename in ['GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md','GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.html']:
 content=(DEST/filename).read_text(encoding='utf-8')
 urls=re.findall(r'\]\(([^)]+)\)',content) if filename.endswith('.md') else re.findall(r'(?:href|src)="([^"]+)"',content)
 for url in urls:
  if url.startswith(('http:','https:','#')):continue
  p=DEST/url.split('#')[0]
  references.append(url)
  if not p.exists():missing.append((filename,url))
if missing:raise RuntimeError(f'Missing document links: {missing}')
# Check numerical inventories against the full uncompressed data before delivery.
inventory=json.loads(gzip.decompress((DEST/'assets_inventory.json.gz').read_bytes()))
assert inventory['asset_count']==774 and len(inventory['assets'])==774
assert sum(inventory['frames_by_role'].values())==185335
assert sum(inventory['substantial_frames_by_role'].values())==153422
from PIL import Image
for file in list((DEST/'palette').glob('*.png'))+list((DEST/'palette').glob('*.webp')):
 with Image.open(file) as im:im.verify()
files=[p for p in DEST.rglob('*') if p.is_file() and p.name!='delivery_verification.json']
report={'author':'Codex','local_link_references_verified':len(references),'missing_links':missing,
        'files':len(files),'bytes':sum(p.stat().st_size for p in files),
        'inventory_assets':774,'sha256_guide_md':hashlib.sha256((DEST/main_files[0]).read_bytes()).hexdigest(),
        'sha256_guide_html':hashlib.sha256((DEST/main_files[1]).read_bytes()).hexdigest(),
        'ingame_validation':False,'claude_audits_read':False}
(DEST/'delivery_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'destination':str(DEST),**report},indent=2))
