"""Record the completed correction preview, without changing production authorities."""
from prepare import ROOT,BASE,OUT,load,save
import effect_workflow as workflow
from pathlib import Path

def main():
    plan=load(OUT/'plan.json');check=load(OUT/'verification.json')
    assert check['status']=='passed' and check['contexts']==99 and check['corrected_assets']==27
    jobs=plan['jobs'];results=[load(OUT/'results'/f'{a["job_id"]}.json') for a in jobs]
    assert len(results)==99 and all(r['passed'] for r in results)
    proofs=[workflow.file_evidence(ROOT,p) for p in sorted(Path(__file__).parent.glob('*.py'))]
    summary={'schema':'bg2-effects-correction-preview-v1','date':'2026-10-19',
        'parent':workflow.file_evidence(ROOT,BASE/'production.json'),
        'verification':workflow.file_evidence(ROOT,OUT/'verification.json'),
        'assets':31,'contexts':99,'corrected_assets':27,'corrected_contexts':95,
        'rebout_assets':10,'rebout_contexts':sum(a['rebout'] for a in jobs),
        'smoothed_assets':24,'smoothed_contexts':sum(a['smooth'] for a in jobs),
        'retimed_assets':[12,20,30],'black_neutral_assets':[12,14,20],
        'unchanged_assets':[24,25,28,29],
        'phases':sum(len(r['frames']) for r in results),'profiles':sum(len(r['profiles']) for r in results),
        'all_parent_durations_exact':True,'geometry':'20px x4 transparent pad, centre+5x1; world positions retained',
        'native_fps':'15FPS compatibility basis inherited; not an ingame cadence measurement',
        'recipe':proofs,'preview':'http://127.0.0.1:8794/?v=corrections31',
        'production_registry_changed':False,'qa':'pending-user-preview','installed':False,'release_changed':False}
    save(OUT/'result.json',summary)
    rows=[]
    for a in plan['assets']:
        matches=[j for j in jobs if j['resref']==a['resref']];j=matches[0]
        actions=[name for yes,name in [(j['rebout'],'ReboutCX x4'),(j['smooth'],'Bézier +fondu alpha'),(j['retime'],'temps natif'),(j['black_neutral'],'noir transparent')] if yes] or ['conservé']
        rows.append(f"|{a['ordinal']:02d}|{a['resref']}|{len(matches)}|{', '.join(actions)}|")
    text='''# Lot31 — corrections demandées, aperçu2026-10-19

- Autorisation :10effets ReboutCX+lissage,13lissage seul,12/20chronologie+noir transparent,30chronologie+lissage,14noir transparent.24/25/28/29 conservés.
- Résultat :27BAM/95contextes corrigés ; comparatif31BAM/99contextes,9968phases/658profils. [Synthèse](result.json), [vérification](verification.json), [plan exact](plan.json).
- [Galerie](http://127.0.0.1:8794/?v=corrections31) : vanilla/précédent/correction, horloge/cadrage communs ; palette/cycle/mode/phase/zoom/alpha/fond/mélange sélectionnables.30/31 démarrent en boucle. Les vues natives utilisent la même base15FPS de compatibilité ; aucune mesure ingame supplémentaire déduite.
- ReboutCX :10BAM/41palettes, modèle x4 FP16 ; entrées natives recolorées avant inférence, remplissage RGB du transparent par plus proche opaque, alpha traité séparément. Manifestes `reboutcx/*/manifest.json` ; autres effets RGB précédents conservés sauf réinterpolation12/20/30 et conversion transparente12/14/20.
- Masques24BAM : méthode SPDEATH3, Potrace alphamax1.334/opttol0.1/turdsize0/SS8 sans clamp nearest ; poses natives tracées avant interpolation alpha. Fondu Gaussian du contour seul, sigma≤4x4 adapté localement0.5..4 pour préserver traits fins ; aucun retrait. RGB existant exact en zone commune pour lissage seul. `masks/*/report.json` : aucune composante native totalement effacée. Topologie tous seuils non garantie.
-12 SPRDRABU :9cycles20slots,8poses visibles puis12slots vides.20 SPNPOISI :40slots,20poses visibles puis20slots vides. Ancienne méthode étirait les poses visibles sur les réserves invisibles. Nouveau temps : ancres natives conservées, Apollo15→30 sur entrées adjacentes distinctes puis réinsertion des véritables holds. En once,12vide dès8/15s et20dès20/15s ; durée totale20/15s et40/15s. Une image vide stockée et référencée plusieurs fois : pas de mouvement inventé pendant une pause native.
-30 SANCTRY :12poses actives distinctes6..17 ;0..5 inutilisées, pas de double actif exact à retirer. Nouvelle interpolation15→30 incluant dernière→première en boucle ; ancien aperçu rejouait la variante once, provoquant une coupure. Durée12/15s conservée. `timing-audits/` : ancres/inputs/rationnels.
-12/14/20 : noir neutre encodé dans l'alpha (`A'=round(A*max(RGB)/255)`, RGB droit renormalisé depuis flux prémultiplié). Noir exact RGBA0 ; énergie lumineuse conservée≤1octet, encodages droit/prémultiplié vérifiés. Pas de clé noire globale appliquée aux autres assets.
- Géométrie : marge20px x4 (=5x1) commune, centre+5x1 ; positions monde inchangées. Futur carrier/pack devra encoder cette marge. Données candidates `rgba/` +`results/*.json` ; pas de pack runtime/index/QA/install/release changé par cet essai. Productions historiques et installation restent distinctes. Sources et manifestes parents vérifiés.
- Vérification :99contextes, tous profils/durées exacts ; RGBA/hash/PNG, prémultiplication, bords transparents, RGB lissage seul, alpha reconstruit, noirs et pauses natives. Doublons temporels permis seulement pour pause native/image vide. `verification/*.json`.
- Recette : `pipeline/recipes/effects-lot31-corrections-20261018-v1/`. Fichiers ignorés (RGBA,PNG,NPZ,entrées Apollo) restent dans ce dossier ; aucune purge.

|N°|BAM|Palettes|Correctif|
|---|---|---|---|
'''
    (OUT/'README.md').write_text(text+'\n'.join(rows)+'\n',encoding='utf-8')
    print('Recorded completed correction preview:',summary['phases'],'phases',flush=True)

if __name__=='__main__':main()
