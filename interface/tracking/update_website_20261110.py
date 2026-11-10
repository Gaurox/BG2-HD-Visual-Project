"""Update only the canonical website UI progress snapshot; no commit/push/deploy."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
site=get_path('website_checkout',required=True)
snapshot=json.loads((ROOT/'interface/tracking/progress.json').read_text(encoding='utf-8'))
assert (snapshot['total'],snapshot['produced'],snapshot['partial_production'],snapshot['qa_observed_normal'])==(204,6,1,4)
for lang in ('en','fr'):
 file=site/('fr/progress.html' if lang=='fr' else 'progress.html')
 s=file.read_text(encoding='utf-8');fr=lang=='fr'
 # Keep all other domain ratios and workload weights exactly as documented.
 phase=10+5+5+5*.95+32.5+32.5+2*(6/204+5/50+242/243)
 assert round(phase,1)==92.0
 s=s.replace('91.9','92.0').replace('91,9','92,0')
 s=s.replace('UI = 2/1672','UI = 0/204 fully reconciled; 4 normal-state observations retained')
 pattern=r'          <article class="track" style="--total: 1672; --produced: 2; --qa: 2; --release: 2" data-reveal>.*?</article>'
 title='Interface &amp; HUD' if fr else 'UI &amp; HUD'
 label='204 ressources retenues' if fr else '204 retained resources'
 aria='Interface et HUD : 6 ressources avec exports x4 complets sur 204 ; QA complète et release à réconcilier' if fr else 'UI and HUD: 6 resources with complete x4 exports out of 204; full QA and release reconciliation pending'
 stats='<li><b>6</b> exports x4 complets</li><li><b>1</b> ressource partiellement produite</li><li><b>4</b> observées au démarrage normal</li>' if fr else '<li><b>6</b> complete x4 exports</li><li><b>1</b> partially produced resource</li><li><b>4</b> observed at normal startup</li>'
 note='Périmètre réduit aux fonds, panneaux et illustrations retenus ; boutons et petites icônes retirés du travail à faire. 197 ressources restent à évaluer avant toute nouvelle production. La QA complète par ressource et la release restent à réconcilier ; les preuves des deux groupes de menus historiques sont conservées. Les quatre observations du sélecteur couvrent son démarrage normal, sans validation séparée des survols.' if fr else 'Scope reduced to retained backgrounds, panels and artwork; buttons and small icons removed from the work queue. Existing production remains to be assessed for 197 resources before generating new assets. Full resource QA and release reconciliation remain pending; evidence for the two historical menu groups is preserved. The four selector observations cover normal startup, without separate hover-state approval.'
 block=f'''          <article class="track" id="ui-hud" style="--total: 204; --produced: 6; --qa: 0; --release: 0" data-reveal>
            <div class="track-id"><h3>{title}</h3><span>{label}</span></div>
            <div class="track-meter">
              <div class="track-bar" role="img" aria-label="{aria}">
                <i class="bar-produced"></i><i class="bar-qa"></i><i class="bar-release"></i>
              </div>
              <span class="track-pct">{'2,9 %' if fr else '2.9%'}</span>
            </div>
            <ul class="track-stats">{stats}</ul>
            <p class="overall-progress-note">{note}</p>
          </article>'''
 s,count=re.subn(pattern,lambda m:block,s,flags=re.S);assert count==1,f'{file}: expected one legacy UI track, got {count}'
 file.write_text(s,encoding='utf-8')
copy=dict(snapshot,source_repository='Gaurox/BG2-HD-Visual-Project',source_path='interface/tracking/progress.json',note='Manually refreshed snapshot; never a production/QA authority.')
(site/'assets/ui-progress.json').write_text(json.dumps(copy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
f=site/'README.md';s=f.read_text(encoding='utf-8');s+='''
## UI/HUD scope snapshot — 2026-11-10

- Authority: project `interface/index/work-tracking.json`; exported `interface/tracking/progress.json`.
- Local copy: `assets/ui-progress.json`; EN/FR progress tracks updated together.
- 204 selected logical resrefs replace 1672 raw resources; buttons/small icons no longer pending.
- 6 complete existing x4 outputs, 1 partial, 197 production states to assess; no fresh inference.
- 4 selector resources observed at normal startup. Full-frame QA and release not reconciled:
  zero in comparable bars means no completed reconciliation, not erased historical acceptance.
- Two legacy menu groups retained in project tracker, never counted as two individual resources.
- Phase 1: 92.0% using unchanged weights and 6/204 UI production. In-game aggregate: unchanged 91.4%.
''';f.write_text(s,encoding='utf-8')
print('Updated canonical website: progress.html, fr/progress.html, assets/ui-progress.json, README.md')
