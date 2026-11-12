"""Record only the completed OUTRO production; keep visual/ingame acceptance separate."""
from pathlib import Path
import csv,json

ROOT=Path(__file__).resolve().parents[3]

def main():
    manifest=json.loads((ROOT/'video/index/outro-finals30-20261112-v1.json').read_text())
    assert manifest['state']=='runtime-ready' and not manifest['installed']
    path=ROOT/'video/index/status.csv'
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    row=next(r for r in rows if r['asset_key']=='movie:default:OUTRO')
    assert row['production_state']=='not-started'
    row.update(retained_output=manifest['files']['preview']['path'],production_state='produced',
        qa_scope='technical-verified-visual-pending')
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    assert sum(r['production_state']=='produced' for r in rows)==22
    assert sum(r['production_state']=='not-started' for r in rows)==14
    resources={r['asset_key']:r for r in csv.DictReader((ROOT/'video/index/resources.csv').open(encoding='utf-8-sig'))}
    remaining=[r for r in rows if r['production_state'] in ('not-started','partial-paused')]
    total=sum(int(resources[r['asset_key']]['duration_ms']) for r in remaining)
    assert len(remaining)==15 and total==377061
    path=ROOT/'video/SUIVI.md';text=path.read_text(encoding='utf-8')
    text=text.replace('# Suivi vidéo — 2026-11-11','# Suivi vidéo — 2026-11-12',1)
    text=text.replace('21productions complètes,1partielle en pause (ENDCRDIT),15sans production ;16cinématiques à terminer (≈7min39s de sources entières).',
        '22productions complètes,1partielle en pause (ENDCRDIT),14sans production ;15cinématiques à terminer (≈6min17s de sources entières).',1)
    text=text.replace('`index/endings-finals30-20261111-v1.json` ; QA=',
        '`index/endings-finals30-20261111-v1.json`, `index/outro-finals30-20261112-v1.json` ; QA=',1)
    text=text.replace('## À terminer — 16cinématiques','## À terminer — 15cinématiques',1)
    text=text.replace('`OUTRO`, ','',1)
    text=text.replace('Sources entières cumulées458,727s (≈7min39s) ;15états `not-started`',
        'Sources entières cumulées377,061s (≈6min17s) ;14états `not-started`',1)
    marker='\n## ENDCRDIT — pause après première portion'
    assert marker in text and '## OUTRO —' not in text
    section=('\n## OUTRO — production FullHD30 prête au contrôle\n\n'
        '- Source muette1225images15fps →4portions SeedVR2 3B FP16 LAB/1080 (contexte33images) →master1225images →Apollo8/2450images30fps (~81,667s). MP4,MKV,WBM restent sans piste audio.\n'
        '- Résultats/contrôles : `index/outro-finals30-20261112-v1.json` ; recette `../pipeline/recipes/outro-seedvr-apollo30-20261112-v1/README.md`. QA visuelle utilisateur en attente ; aucune installation ou intégration release.\n')
    path.write_text(text.replace(marker,section+marker,1),encoding='utf-8')
    path=ROOT/'video/README.md';text=path.read_text(encoding='utf-8');marker='\nEND15FPS/MELISSAN finales'
    assert marker in text and 'OUTRO finale2026-11-12' not in text
    para=('\nOUTRO finale2026-11-12 : SeedVR FP16 LAB →Apollo8 FullHD30,2450images/~81,667s,sans audio comme la source ; MP4/MKV/WBM prêts techniquement au contrôle,QA visuelle/ingame non acquises. Résultats : `index/outro-finals30-20261112-v1.json` ; [recette](../pipeline/recipes/outro-seedvr-apollo30-20261112-v1/README.md). Aucune installation/release.\n')
    path.write_text(text.replace(marker,para+marker,1),encoding='utf-8')
    print('OUTRO recorded; 22 produced, 1 partial-paused, 14 not-started; 15 remaining,377.061s')

if __name__=='__main__':main()
