"""Record completed production without inferring visual or ingame acceptance."""
from spatial import *
import csv,io,shutil
def main():
 m=json.loads((ROOT/'video/index/endcrdit-proteus-T1-finals30-20261112-v1.json').read_text(encoding='utf-8'));assert m['state']=='runtime-ready' and m['frames']==4004
 production=json.loads((RUN/'production.json').read_text(encoding='utf-8'));production.update(state='runtime-ready',final_manifest='video/index/endcrdit-proteus-T1-finals30-20261112-v1.json',full_visual_qa='pending',installed=False);save(RUN/'production.json',production)
 for name in ('production.json','spatial-verification.json','proteus-T1-commands.json','apollo-verification.json','apollo-commands.json'):
  shutil.copy2(RUN/name,RECIPE/'metadata'/name)
 save(RUN/'completion.json',dict(state='runtime-ready',manifest='video/index/endcrdit-proteus-T1-finals30-20261112-v1.json',installed=False))
 p=ROOT/'video/index/status.csv';rows=list(csv.DictReader(p.open(encoding='utf-8-sig')))
 row=next(x for x in rows if x['asset_key']=='movie:default:ENDCRDIT');row.update(retained_output=m['files']['preview']['path'],production_state='produced',qa_scope='T1-first5s-accepted-full30-pending',installation_state='not-installed',ingame_qa='not-performed',release_state='not-integrated')
 def csvsave(p,rows):
  s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows);p.write_text(s.getvalue(),encoding='utf-8')
 csvsave(p,rows)
 p=ROOT/'video/index/processing.csv';rows=list(csv.DictReader(p.open(encoding='utf-8-sig')));assert not any(x['asset_key']=='movie:default:ENDCRDIT' for x in rows)
 row={k:'' for k in rows[0]};row.update(asset_key='movie:default:ENDCRDIT',asset_id='videos:movie-default-endcrdit',asset_directory='video/endcrdit',upscale_run='endcrdit-proteus-T1-apollo30-20261112-v1',upscale_state='produced',interpolation_run='endcrdit-proteus-T1-apollo30-20261112-v1',interpolation_state='produced',validation_scope='T1-first5s-accepted-full30-pending',patch_state='not-integrated',notes='Proteus prob-4 T1 neutre x2 puis Lanczos1080;2001images natives;Apollo8 4001images generees+3tenues=4004images30fps;audio natif MKV/WBM identique;T1 seul choisi utilisateur2026-11-12;secondes passes et SeedVR non selectionnes;QA visuelle film complet en attente;non installe;index/endcrdit-proteus-T1-finals30-20261112-v1.json');rows.append(row);csvsave(p,rows)
 p=ROOT/'video/SUIVI.md';s=p.read_text(encoding='utf-8');s=s.replace('36productions complètes,1partielle en pause (ENDCRDIT),0sans production ;1cinématique à terminer (≈2min13s de source entière)','37productions complètes,0partielle,0sans production ;aucun traitement initial restant ;QA visuelle du film complet ENDCRDIT30 en attente')
 at=s.index('| LOGO |');s=s[:at]+'| ENDCRDIT | Proteus T1 neutre →Apollo8,4004images/FullHD30/~133,47s,son natif complet | T1 accepté sur5s ;film complet30fps en attente | non installé |\n'+s[at:]
 start=s.index('## ENDCRDIT —');end=s.index('## DAYNITE — chaîne conservée',start)
 block='''## ENDCRDIT — production complète T1 + Apollo30

- Choix utilisateur2026-11-12 :T1 Proteus neutre seul ;secondes passes et nearest720→SeedVR7B non sélectionnés. QA extrait T1 : `index/qa-decisions/ENDCRDIT/20261112-topaz-T1-first5s-visual-accepted-v1.json` ;choix production complète : `index/qa-decisions/ENDCRDIT/20261112-T1-single-pass-full-production-selected-v1.json`.
- Source2001images1280×720/15fps →Proteus prob-4 neutre x2/2560×1440 puis Lanczos1080 →Apollo8 :4001images générées+3tenues terminales=4004images/1920×1080/30fps/~133,47s ;origine PTS et audio natif complet conservés. Une seule passe spatiale ;aucun SeedVR. MP4/AAC,MKV/Vorbis,WBM VP8/Vorbis ;comptes/décodage/PTS/audio/SSIM vérifiés.
- Résultats : `index/endcrdit-proteus-T1-finals30-20261112-v1.json` ;[recette](../pipeline/recipes/endcrdit-proteus-T1-apollo30-20261112-v1/README.md). **QA visuelle film complet30fps en attente**,aucune installation/release.
- Historique conservé :préfixe SeedVR330images rejeté pour lettres déformées,checkpoint `index/endcrdit-paused-20261111-v1.json` et anciens essais inchangés ;cet ancien checkpoint ne décrit pas la production courante.
- Essais0–5s :[14variantes initiales](../pipeline/recipes/endcrdit-topaz-tests-5s-20261112-v1/README.md),[secondes passes](../pipeline/recipes/endcrdit-topaz-second-pass-5s-20261112-v1/README.md),[nearest720 puis7B](../pipeline/recipes/endcrdit-T1-nearest720-seedvr7b-5s-20261112-v1/README.md). T1 reste le seul choix retenu.

## Production — 37cinématiques complètes

-0état `not-started` ou `partial-paused` ;13tutoriels exclus,50sources conservées.32versions installées/validées ingame ;ENDCRDIT non installé et film complet30fps à valider. QA/installation/release restent séparées.

'''
 s=s[:start]+block+s[end:];p.write_text(s,encoding='utf-8')
 p=ROOT/'video/README.md';s=p.read_text(encoding='utf-8');at=s.index('QA ingame2026-11-12');s=s[:at]+'ENDCRDIT produit2026-11-12 :**T1 Proteus neutre seul +Apollo8 FullHD30**,4004images/~133,47s,audio natif complet. T1 accepté sur5s ;**QA film complet30fps en attente**,non installé. [Recette](../pipeline/recipes/endcrdit-proteus-T1-apollo30-20261112-v1/README.md),manifeste `index/endcrdit-proteus-T1-finals30-20261112-v1.json`.37cinématiques désormais produites ;anciens essais/pauses conservés comme historique.\n\n'+s[at:];p.write_text(s,encoding='utf-8')
 print('ENDCRDIT_TRACKING_PRODUCED_QA_PENDING',flush=True)
if __name__=='__main__':main()
