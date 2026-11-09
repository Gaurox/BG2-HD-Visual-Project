"""Record bounded production exclusions; never grant QA or modify installed assets."""
import csv,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
import effect_tracking as t
import effect_authority as authority
OUT=ROOT/'effects/research/residual-usage-audit-20261109-v2'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(w.json_bytes(d))

def main():
    assert not (OUT/'dispositions.json').exists()
    scan=load(OUT/'scan-summary.json');sources=load(OUT/'sources.json');refs=load(OUT/'references.json')
    follow=load(OUT/'followup-references.json');areas=load(OUT/'typed-areas.json')
    assert len(sources)==67
    for n in ['GUILLOT1','GUILLOT2','ENTTEST1']:assert not follow.get(n)
    for n in ['MSOLG1','SPAURAFD']:
        assert all(h['owner'].upper()==n and h['type']=='VVC' and h['offset']==8 for h in follow[n])
    assert load(OUT/'alias-runtime.json')['pixels_geometry_timeline_identical']
    assert b'resref=MSOG' in (OUT/'7F3B.ini').read_bytes()
    # All primary states are kept byte-identical, including the two missing sources.
    for p,sha in scan['unchanged_inputs'].items():assert w.sha256_file(ROOT/p)==sha
    result=[]
    for src in sources:
        n=src['resref'];category='unreferenced-bam-current-graph'
        reason='BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.'
        domain='dormant-resources';risk='Generated/mod-specific references cannot be ruled out universally.'
        if n in ['SHGLYPH','SHSKULL']:
            category='native-projectile-shadow';domain='projectiles'
            reason='Champ PRO shadow-animation 0x10C ; masque natif native-mask-no-ai déjà identifié dans projectiles/index/visual-assets.csv. Conserver natif ; aucune nouvelle QA déduite.'
        elif n=='SP_DEMGT':
            category='already-produced-alias';domain='effects'
            reason='Alias exact AMDEMGT accepté ; images, géométrie et timeline installées identiques. Aucune nouvelle inférence ; QA indépendante de cet alias non inventée.'
        elif n in ['SPAURAFD','SPENTAXL']:
            category='missing-source-orphan-controller';domain='effects'
            reason=('VVC '+('SPAURAFD' if n=='SPAURAFD' else 'ENTTEST1')+' référence un BAM absent de KEY/override/source local ; aucun appelant du contrôleur trouvé. Conserver blocked, ne pas fabriquer une image.')
        elif n=='MSOLG1':
            category='legacy-solar-orphan-vvc';domain='sprites-legacy'
            reason='Sprite Solar historique ; VVC MSOLG1 sans appelant trouvé. ANISND mentionne MSOL, mais le profil actif 7F3B.INI utilise resref=MSOG, confirmé par sprite/index/sprite_animations.csv. Pas de second traitement du Solar.'
        elif n in ['AM307TT2','AM307TT3']:
            category='dormant-effect-script';domain='effects'
            script='GUILLOT1' if n.endswith('2') else 'GUILLOT2'
            reason=f'{script}.BCS contient action272 CreateVisualEffect({n}), mais aucun appelant de {script} trouvé. Références AR0329.BCS = action301 AmbientActivate, pas création graphique. ARE0307/0329 utilisent AM307TT1 déjà accepté ; aucun nouveau job confirmé.'
        elif n=='SPWI124B':
            category='active-ui-icon';domain='icons'
            reason='Six SPL actifs référencent SPWI124B dans extended-header+0x04 (icône mémorisée), dont SPWI124. Travail éventuel à suivre dans icons, pas comme effet du monde ; aucune QA/production UI déduite.'
        elif n=='SPWI124A':
            category='ui-variant-no-direct-caller';domain='icons'
            reason='Variante graphique d’icône/parchemin, sans appelant exact trouvé. SPWI124 utilise icône de livre C et icône mémorisée B ; conserver A comme variante à qualifier côté icons.'
        elif n in ['AM0411A','AM0411B','AM2000B1','AM2000B2','AM2000B3','AM2000B4']:
            category='sound-homonym';domain='dormant-resources'
            reason='Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.'
        elif n in ['AM0902L1','AM0902L2','AM0902L3','AM0902L4']:
            category='ambient-name-homonym';domain='dormant-resources'
            reason='AR0902.BCS emploie le nom comme objet sonore pour action301 AmbientActivate. La vraie animation placée est AM0902L, déjà acceptée côté animations ; aucun BAM suffixé appelé.'
        elif n=='TREE01':
            category='door-name-homonym';domain='dormant-resources'
            reason='Références dans noms/IDs de portes ARE/WED et opérations de porte BCS ; aucune animation BAM TREE01 placée. Le BAM d’arbre n’est pas le dessin des tuiles de cette porte.'
        elif n=='0202A':
            category='substring-false-hit';domain='dormant-resources'
            reason='Les occurrences texte sont des suffixes de AM0202A, pas un champ BAM 0202A. Animation active AR0202 = AM0202A déjà acceptée ; BAM différent, sans nouvel appel identifié.'
        if n.startswith('DEMB'):
            reason+=' Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.'
        if n in ['DEMB1A7','DEMB1A9']:reason+=' DEMB1A7/DEMB1A9 = doublon canonique strict.'
        result.append({'resref':n,'category':category,'production_scope':'excluded-current-effects-production',
            'domain':domain,'reason':reason,'source_sha256':src.get('source_sha256'),
            'canonical_sha256':src.get('canonical_sha256'),'reference_count':len(refs.get(n,[])),
            'source_state':src['source_state'],'qa_granted':False,'limits':risk})
    counts=dict(Counter(r['category'] for r in result))
    payload={'schema':'bg2-effects-residual-dispositions-v1','date':'2026-11-09','rows':result,'category_counts':counts,
        'confirmed_required_world_effect_jobs':0,'active_ui_icon_handoff':['SPWI124B'],'ui_variant_handoff':['SPWI124A'],
        'dormant_graphics_cases':['AM307TT2','AM307TT3','MSOLG1'],'missing_sources':['SPAURAFD','SPENTAXL'],
        'scope':'Installed game native KEY/BIF + effective overrides + source indexes; static graph audit, not an ingame execution trace.',
        'scan':w.file_evidence(ROOT,OUT/'scan-summary.json'),'followup':w.file_evidence(ROOT,OUT/'followup-references.json'),
        'typed_areas':w.file_evidence(ROOT,OUT/'typed-areas.json'),'alias_runtime':w.file_evidence(ROOT,OUT/'alias-runtime.json'),
        'limits':['No caller found is bounded evidence for this installation, not a proof about all possible mods/generated names.',
                  'Dormant BAM/VVC/BCS preserved; new native/mod invocation reopens only the matching asset.',
                  'Missing-source states, QA, production, installation, release and GPU pause are preserved.']}
    save(OUT/'dispositions.json',payload)
    # Sparse usage overrides are the intended queue authority; do not rewrite generated inventories.
    with authority.guard(ROOT,True):
        current=t.load_classification(ROOT);save(OUT/'classification-before.json',current)
        for r in result:
            node=current['assets'].setdefault(r['resref'],{})
            node.update(usage='excluded',priority=999,notes='Audit2026-11-09 : '+r['reason']+' Preuve=effects/research/residual-usage-audit-20261109-v2/dispositions.json ; exclusion de production effects seulement, aucune QA acquise.')
        authority.commit(ROOT,{t.CLASSIFICATION:w.json_bytes(current)})
    t.load_classification(ROOT)
    queue=t.queue(ROOT,1000)
    for p,sha in scan['unchanged_inputs'].items():assert w.sha256_file(ROOT/p)==sha
    save(OUT/'verification.json',{'passed':True,'rows':67,'classification_rows_updated':67,
        'production_qa_installation_release_unchanged':True,'gpu_used':False,'queue_counts':queue['counts'],
        'effective_world_effect_jobs_confirmed':0,'dormant_cases_preserved':3})
    note='Audit2026-11-09 : 67entrées résiduelles examinées ; 0nouveau job d’effet du monde confirmé dans le graphe courant. 3cas dormants AM307TT2/3/MSOLG1 conservés ; 2BAM absents derrière contrôleurs sans appelant ; SPWI124B actif = icône, renvoi icons. Exclusions de production uniquement, aucune QA inventée.'
    text='# Reliquat effets — audit des usages\n\n- '+note+'\n- `scan-summary.json` : '+str(sum(scan['resource_counts'].values()))+' ressources natives/overrides, '+str(scan['scanned_bytes'])+'octets, métadonnées + scripts + contrôleurs + EXE ; index ARE/sprites croisés.\n- `native-residual-contact-sheet.png` : inspection CPU des65sources présentes ; `sources.json` : SHA, géométrie, cycles, stats.\n- `references.json` = candidats bruts, **pas preuve de rendu**. `typed-areas.json` et `followup-references.json` séparent WAV, noms, icônes, faux suffixes et contrôleurs sans appelants.\n- Guillotines : appels272 réels dans GUILLOT1/2 mais scripts orphelins dans le graphe actuel ; AR0329 emploie action301 sonore. Aucun lien vers ces scripts dans les ARE/CRE/BCS/DLG/2DA/INI natives/overrides. Ne pas lancer un job sur la seule présence du script.\n- Solar : ANISND MSOL historique ; INI actif7F3B utilise **MSOG**, pas MSOLG1. VVC MSOLG1 orphelin ; aucun second job du Solar.\n- SP_DEMGT : alias installé identique AMDEMGT accepté ; pas de nouvelle production, QA propre à l’alias non inférée.\n- SHGLYPH/SHSKULL : ombres PRO natives ; préserver. SPAURAFD/SPENTAXL restent bloqués source absente ; ne pas supprimer leurs contrôleurs.\n- **Limite** : audit statique de cette installation, pas preuve universelle d’inutilisation ni QA ingame. Toute nouvelle invocation/mod réouvre la ressource correspondante.\n- `classification.json` : usage excluded appliqué au périmètre effects ; processing/QA/install/release intacts. Les2sources manquantes restent blocked dans la queue.\n- Formats primaires : [ARE](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/are_v1.htm), [SPL](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/spl_v1.htm), [actions272/301](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm).\n\n| Catégorie | Entrées |\n|---|---:|\n'+''.join(f'|{k}|{v}|\n' for k,v in counts.items())+'\n## Décisions par ressource\n\n| BAM | Décision | Motif |\n|---|---|---|\n'+''.join(f'|{r["resref"]}|{r["category"]}|{r["reason"]}|\n' for r in result)
    (OUT/'README.md').write_text(text,encoding='utf-8')
    handoff=ROOT/'icons/research/effects-residual-handoff-20261109-v1';handoff.mkdir(parents=True,exist_ok=False)
    (handoff/'README.md').write_text('# Icônes repérées dans le reliquat effects\n\n- SPWI124B : icône mémorisée active, champ SPL extended-header+0x04, 6propriétaires SPWI124/OHNRDKIL/OHNRDTEL/OHNVRD1/2/3. Hors effets du monde ; aucune production/QA UI acquise.\n- SPWI124A : variante parchemin sans appelant exact trouvé ; à qualifier côté icons, pas un job effects.\n- Le suivi généré icons recense SPWI124C (livre) ; ne pas assimiler la présence du C à une production du B. Aucun index généré régénéré ici.\n- Preuves : [audit67](../../../effects/research/residual-usage-audit-20261109-v2/README.md), `references.json`, `dispositions.json`.\n',encoding='utf-8')
    for path in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
        text=path.read_text(encoding='utf-8-sig');i=text.index('\n')+1
        path.write_text(text[:i]+'\n**Reliquat audité — 2026-11-09** : [décisions67](research/residual-usage-audit-20261109-v2/README.md). '+note+'\n'+text[i:],encoding='utf-8')
    print('DONE',counts,'queue',queue['counts'])

if __name__=='__main__':main()
