"""Refresh only the bilingual UI/HUD progress from the canonical local tracker."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
site=get_path('website_checkout',required=True);snapshot=json.loads((ROOT/'interface/tracking/progress.json').read_text(encoding='utf-8'));total=snapshot['total'];produced=snapshot['produced'];observed=snapshot['qa_observed_resources']+snapshot['qa_observed_normal'];pending=snapshot['next_actions'].get('user-ingame-test-next-ten',0);unassessed=snapshot['next_actions']['qualify-usage-and-existing-production'];assert (total,produced,observed,pending)==(204,21,9,10)
for lang in ['en','fr']:
 fr=lang=='fr';file=site/('fr/progress.html' if fr else 'progress.html');s=file.read_text(encoding='utf-8')
 # Unchanged weights and other track ratios, read from the live source document.
 tracks=re.findall(r'<article class="track[^>]*style="([^"]+)"[^>]*>\s*<div class="track-id"><h3>(.*?)</h3>',s,re.S)
 values=[]
 for style,label in tracks:
  v={k:float(n) for k,n in re.findall(r'--(total|produced|qa|release):\s*([0-9.]+)',style)};values.append(v)
 assert len(values)==12
 ratios=[v['produced']/v['total'] for v in values]
 phase=5*ratios[0]+5*ratios[2]+5*ratios[5]+5*ratios[4]+5*ratios[1]+32.5*ratios[3]+32.5*ratios[6]+2*(produced/total+sum(ratios[8:12]))
 newphase=f'{phase:.1f}';oldphase=re.search(r'--phase-progress:\s*([0-9.]+)',s)[1];s=s.replace(oldphase,newphase).replace(oldphase.replace('.',','),newphase.replace('.',','));assert newphase=='92.1'
 pattern=r'          <article class="track" id="ui-hud".*?</article>'
 title='Interface &amp; HUD' if fr else 'UI &amp; HUD';label='204 ressources retenues' if fr else '204 retained resources';pct=f'{100*produced/total:.1f}';pct=pct.replace('.',',')+' %' if fr else pct+'%'
 aria=f'Interface et HUD : {produced} ressources produites sur {total}, {observed} observées en jeu avec périmètre limité ; dix nouveaux assets à tester' if fr else f'UI and HUD: {produced} produced resources out of {total}, {observed} observed in game with limited coverage; ten new assets awaiting tests'
 stats=f'<li><b>{produced}</b> ressources x4 retenues</li><li><b>{observed}</b> observées en jeu</li><li><b>{pending}</b> nouvelles installées à tester</li>' if fr else f'<li><b>{produced}</b> retained x4 resources</li><li><b>{observed}</b> observed in game</li><li><b>{pending}</b> newly installed, awaiting tests</li>'
 note=f'Fonds, panneaux et illustrations uniquement ; boutons et petites icônes hors travail actif. Quatre menus SeedVR 7B x4 validés sur le rendu observé : inventaire, personnage, options et journal, avec la feuille superposée du journal. Dix panneaux supplémentaires retenus et installés pour test. Les neuf ressources observées incluent quatre observations du sélecteur au démarrage normal ; aucun audit exhaustif de tous les états ni nouvelle qualification release. {unassessed} ressources restent à évaluer ; BIGLOGO est partiellement produit. Les preuves des deux anciens groupes de menus sont conservées.' if fr else f'Backgrounds, panels and artwork only; buttons and small icons are outside the active queue. Four SeedVR 7B x4 menus accepted for the observed rendering: inventory, character, options and journal, including its overlaid paper. Ten additional retained panels are installed for testing. The nine observed resources include four normal-startup selector observations; this is not an exhaustive review of every state or new release qualification. Existing production remains to be assessed for {unassessed} resources; BIGLOGO is partially produced. Evidence for the two legacy menu groups is preserved.'
 block=f'''          <article class="track" id="ui-hud" style="--total: {total}; --produced: {produced}; --qa: {snapshot['qa_complete']}; --release: {snapshot['release_confirmed']}" data-reveal>
            <div class="track-id"><h3>{title}</h3><span>{label}</span></div>
            <div class="track-meter">
              <div class="track-bar" role="img" aria-label="{aria}">
                <i class="bar-produced"></i><i class="bar-qa"></i><i class="bar-release"></i>
              </div>
              <span class="track-pct">{pct}</span>
            </div>
            <ul class="track-stats">{stats}</ul>
            <p class="overall-progress-note">{note}</p>
          </article>'''
 s,count=re.subn(pattern,lambda m:block,s,flags=re.S);assert count==1;file.write_text(s,encoding='utf-8')
copy=dict(snapshot,source_repository='Gaurox/BG2-HD-Visual-Project',source_path='interface/tracking/progress.json',note='2026-11-11 manual UI snapshot; observed QA is limited, not full-state QA.')
(site/'assets/ui-progress.json').write_text(json.dumps(copy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=site/'README.md';s=p.read_text(encoding='utf-8');s+='''
## UI/HUD consolidated snapshot — 2026-11-11

- Authority/export unchanged: project `interface/index/work-tracking.json` → `interface/tracking/progress.json`.
- 21/204 retained complete x4 resources (10.3%); BIGLOGO remains partial; 182 production states unassessed.
- 9 logical resources observed in game with limited scope: 4 selector normal-state + 5 resources composing four SeedVR menus.
- Ten further resources retained offline and installed, in-game QA pending; no release payload changed.
- Complete-state QA/release bars remain unreconciled; historical acceptance is retained separately.
- Phase 1: 92.1%, same workload weights; visible-in-game aggregate remains 91.4% under the full-state convention.
''';p.write_text(s,encoding='utf-8');print('Updated FR/EN UI progress, 21/204; phase1 92.1%; no publication')
