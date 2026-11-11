"""Refresh bilingual UI progress from the active tracker; never publish."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

site = get_path('website_checkout', required=True)
summary = json.loads((ROOT / 'interface/tracking/progress.json').read_text(encoding='utf-8'))
tracker = json.loads((ROOT / summary['authority']).read_text(encoding='utf-8'))
total, produced = summary['total'], summary['produced']
observed = summary['qa_observed_resources'] + summary['qa_observed_normal']
pending = sum(r['installation']['state'] == 'installed-for-ingame-test' and
              r['qa']['state'] not in ('accepted-observed-menu', 'accepted-observed-normal', 'accepted-complete') for r in tracker['resources'])
candidates = summary.get('candidate_production', 0)
for language in ('en', 'fr'):
    fr = language == 'fr'
    path = site / ('fr/progress.html' if fr else 'progress.html')
    text = path.read_text(encoding='utf-8')
    tracks = re.findall(r'<article class="track[^>]*style="([^"]+)"[^>]*>\s*<div class="track-id"><h3>(.*?)</h3>', text, re.S)
    values = [{k: float(n) for k, n in re.findall(r'--(total|produced|qa|release):\s*([0-9.]+)', style)}
              for style, _ in tracks]
    assert len(values) == 12
    ratios = [v['produced'] / v['total'] for v in values]
    phase = (5 * ratios[0] + 5 * ratios[2] + 5 * ratios[5] + 5 * ratios[4] + 5 * ratios[1] +
             32.5 * ratios[3] + 32.5 * ratios[6] + 2 * (produced / total + sum(ratios[8:12])))
    old_phase = re.search(r'--phase-progress:\s*([0-9.]+)', text)[1]
    new_phase = f'{phase:.1f}'
    text = text.replace(old_phase, new_phase).replace(old_phase.replace('.', ','), new_phase.replace('.', ','))
    percent = f'{100 * produced / total:.1f}'
    title = 'Interface &amp; HUD' if fr else 'UI &amp; HUD'
    unit = 'ressources retenues' if fr else 'retained resources'
    percent = percent.replace('.', ',') + ' %' if fr else percent + '%'
    aria = (f'Interface et HUD : {produced} ressources retenues sur {total}, {observed} observées en jeu, {pending} ressources installées à tester'
            if fr else f'UI and HUD: {produced} retained resources out of {total}, {observed} observed in game, {pending} installed resources awaiting tests')
    stats = (f'<li><b>{produced}</b> sorties x4 retenues</li><li><b>{observed}</b> ressources observées en jeu</li><li><b>{pending}</b> ressources installées à tester</li>'
             if fr else f'<li><b>{produced}</b> retained x4 outputs</li><li><b>{observed}</b> resources observed in game</li><li><b>{pending}</b> installed resources awaiting tests</li>')
    note = (f'Fonds, panneaux et grandes illustrations ; boutons et petites icônes hors file active. {candidates} ressources produites supplémentaires attendent leur validation. '
            f'Les {observed} observations comprennent les tests de menus et {summary["qa_observed_normal"]} ressources du sélecteur au démarrage normal ; tous les états et variantes ne sont pas extrapolés. '
            'Les barres de QA complète et de release ne comptent que leurs états réconciliés ; les preuves historiques restent conservées. '
            f'{summary["next_actions"].get("qualify-usage-and-existing-production", 0)} ressources restent à rapprocher de l’existant ; BIGLOGO est partiellement produit.'
            if fr else
            f'Backgrounds, panels and large artwork; buttons and small icons are outside the active queue. {candidates} additional produced resources await approval. '
            f'The {observed} observations include menu tests and {summary["qa_observed_normal"]} normal-startup selector resources; other states and variants are not inferred. '
            'Full-QA and release bars count only reconciled states; historical evidence is preserved. '
            f'Existing production remains to be assessed for {summary["next_actions"].get("qualify-usage-and-existing-production", 0)} resources; BIGLOGO is partially produced.')
    block = f'''          <article class="track" id="ui-hud" style="--total: {total}; --produced: {produced}; --qa: {summary['qa_complete']}; --release: {summary['release_confirmed']}" data-reveal>
            <div class="track-id"><h3>{title}</h3><span>{total} {unit}</span></div>
            <div class="track-meter">
              <div class="track-bar" role="img" aria-label="{aria}"><i class="bar-produced"></i><i class="bar-qa"></i><i class="bar-release"></i></div>
              <span class="track-pct">{percent}</span>
            </div>
            <ul class="track-stats">{stats}</ul>
            <p class="overall-progress-note">{note}</p>
          </article>'''
    text, count = re.subn(r'          <article class="track" id="ui-hud".*?</article>', lambda m: block, text, flags=re.S)
    assert count == 1
    path.write_text(text, encoding='utf-8')
copy = dict(summary, installed_candidates_pending=pending, source_repository='Gaurox/BG2-HD-Visual-Project',
            source_path='interface/tracking/progress.json', note='Manual snapshot; limited observed QA and complete-state QA are distinct.')
(site / 'assets/ui-progress.json').write_text(json.dumps(copy, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(retained=produced, observed=observed, candidates=candidates, pending_installed=pending, phase1=new_phase)))

readme = site / 'README.md'
text = readme.read_text(encoding='utf-8')
start, end = '<!-- ui-hud-current-snapshot -->', '<!-- /ui-hud-current-snapshot -->'
section = (f'{start}\n## UI/HUD — current snapshot\n\n'
           f'- Source: project `interface/tracking/progress.json`, {summary["updated_on"]}.\n'
           f'- {produced}/{total} retained complete x4 resources; {candidates} additional candidates, {pending} installed and awaiting tests.\n'
           f'- {observed} resources observed in game with limited coverage; full-state QA and release tracked separately.\n'
           f'- Phase 1 {new_phase}%, unchanged weights. Source inventories and historical evidence preserved.\n{end}')
if start in text:
    text = re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda m: section, text, flags=re.S)
else:
    text += '\n' + section + '\n'
readme.write_text(text, encoding='utf-8')
