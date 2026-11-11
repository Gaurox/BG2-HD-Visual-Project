"""Reconcile only the seven new ending results after their local installation."""
from pathlib import Path
import csv, json, re

ROOT=Path(__file__).resolve().parents[3]

def main():
    production=json.loads((ROOT/'video/index/endings-finals30-20261111-v1.json').read_text())
    installation=json.loads((ROOT/'video/index/endings-ingame-test-20261111-v1.json').read_text())
    assert production['state']=='runtime-ready' and installation['state']=='installed'
    selected={f"movie:{v['locale']}:{v['film']}":v for v in production['variants']}
    path=ROOT/'video/index/status.csv'
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    assert len(selected)==7 and len(rows)==37
    for row in rows:
        if row['asset_key'] in selected:
            v=selected[row['asset_key']]
            row.update(retained_output=v['files']['preview']['path'],production_state='produced',
                qa_scope='technical-verified-visual-pending',installation_state='installed-local-test',
                ingame_qa='pending-user',release_state='not-integrated')
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    resources={r['asset_key']:r for r in csv.DictReader((ROOT/'video/index/resources.csv').open(encoding='utf-8-sig'))}
    remaining=[r for r in rows if r['production_state']=='not-started']
    seconds=round(sum(int(resources[r['asset_key']]['duration_ms']) for r in remaining)/1000)
    produced=sum(r['production_state']=='produced' for r in rows)
    installed=sum(r['installation_state']=='installed-local-test' for r in rows)
    path=ROOT/'video/SUIVI.md';text=path.read_text(encoding='utf-8')
    text=text.replace('`index/processing.csv` et `index/intro-finals30-20261111-v1.json` ; QA=',
        '`index/processing.csv`, `index/intro-finals30-20261111-v1.json` et `index/endings-finals30-20261111-v1.json` ; QA=',1)
    text=re.sub(r'14avec résultat conservé,23sans production ; ≈17min40s de sources restantes\.9installées',
        f'{produced}avec résultat conservé,{len(remaining)}sans production ; ≈{seconds//60}min{seconds%60:02d}s de sources restantes.{installed}installées',text,count=1)
    marker='\n## DAYNITE — chaîne conservée'
    paragraph=('\n## END15FPS / MELISSAN — 7versions installées pour test\n\n'
        '- Production : `index/endings-finals30-20261111-v1.json` ; 2masters SeedVR FP16 LAB → Apollo8 FullHD30,7assemblages à audios Vorbis natifs. Défaut/DE/IT partagent les flux vidéo ; PL recalé sur ses PTS,fin blanche MEL prolongée sans IA supplémentaire.\n'
        '- Installation : `index/endings-ingame-test-20261111-v1.json` ;7WBM canoniques +7alias (`HDENEN/DE/IT/PL`, `HDMLEN/DE/PL`),sauvegardes réelles conservées. QA visuelle utilisateur/ingame en attente ; aucune acceptation ou intégration release déduite.\n'
        '- Console/restauration/réglages : `../pipeline/recipes/endings-shared-30fps-20261111-v1/README.md`.\n')
    assert marker in text and '## END15FPS / MELISSAN' not in text
    text=text.replace(marker,paragraph+marker,1);path.write_text(text,encoding='utf-8')
    path=ROOT/'video/README.md';text=path.read_text(encoding='utf-8')
    marker='\nIntros finales'
    paragraph=('\nEND15FPS/MELISSAN finales2026-11-11 : **7versions FullHD30 installées pour test local**,2masters SeedVR FP16 LAB/Apollo8 partagés, audios natifs et timings PL adaptés ; QA visuelle/ingame en attente. Production : `index/endings-finals30-20261111-v1.json` ; installation : `index/endings-ingame-test-20261111-v1.json` ; [console et restauration](../pipeline/recipes/endings-shared-30fps-20261111-v1/README.md). Aucune intégration release.\n')
    assert marker in text and 'END15FPS/MELISSAN finales' not in text
    path.write_text(text.replace(marker,paragraph+marker,1),encoding='utf-8')
    print('TRACKING',produced,'produced',installed,'installed',len(remaining),'remaining',seconds,'seconds')

if __name__=='__main__':main()
