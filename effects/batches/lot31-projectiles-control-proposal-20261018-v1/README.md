# Proposition lot31 — projectiles, manifestations et contrôle

- Demande2026-10-18 : nouveau gros lot cohérent parmi les restants. **31 BAM distincts /31 RESREF**, disponibles et sans production ; hashes déjà produits et sélections animations exclus. Aucun alias exact à produire en double.
- Source :792enregistrements/97cycles/974slots ; cycles alternatifs, pas une durée globale.183922496octets RGBA x4 aux enregistrements natifs, avant interpolation/contextes de palette.
- Périmètre : animations de projectiles, manifestations de sorts et marques de contrôle/protection ; géométrie native, directions, alpha et recoloration à conserver. Les protections cylindriques forment un sous-groupe distinct.

| Groupe | Nombre | BAM |
|---|---:|---|
| Projectiles physiques |7|ARARROW AXE BOLT DAGGER DART SPEAR TRDARTST|
| Projectiles magiques |9|ACIDBLOB MAGICSTN SPFIREBL SPFLMARR SPRDRABU STNKCLDT TRAVEL WEBENTT BDETHREA|
| Impacts/manifestations |6|SPGREAAI SPGREAXI SPIMPPT SPNPOISI SPRMPARI SPSCHGI|
| Marques au sol/contrôle |7|GLPHWRDH GREASED GREASEH SKLH SPENTACI WEBENTD WEBENTH|
| Protections cylindriques |2|SANCTRY SPSHIELD|

- Usages vérifiés statiquement :13candidats classés via consommateurs PRO/VVC,12via littéraux exacts moteur ;6via champs sémantiques BCS/SPL. Catégories de comptage exclusives, certaines preuves se recouvrent. Aucun affichage réel ni couverture de tous les chemins natifs déduit.
- BCS : SPGREAAI dans ohrcut40/ohrwheel/ohryxtra, SPIMPPT dans CUT217C/CUT218B, SPNPOISI dans TEARDOOR ; actions272/273 CreateVisualEffect/CreateVisualEffectObject. SPL : opcode215, champ ressource SPGREAXI/SPSCHGI dans ohrshad, SPRMPARI dans BALTH08, SPIMPPT dans SPPR728. SHA/offsets/consommateurs dans `batch.json` ; index source global inchangé.
- Doublons :176slots répétés au sein des cycles de7BAM ;2cycles constants. Audit RGBA ancré natif par cycle dans `native-duplicate-audit.json`. Les répétitions non adjacentes ne sont pas des pauses supprimables : conserver positions temporelles/retours de poses et durée native.
- Recette envisagée : SeedVR7B x4, Apollo30 par cycle/direction ; condenser les doublons pour l'inférence et reconstruire sur la chronologie native. Cycles constants conservés ; ne pas concaténer les directions. Cadences/durées selon consommateurs ; pas de15FPS natif affirmé à partir d'un défaut de compatibilité.
- **15BAM tagués palette**, contextes PRO `palette/color_enabled/colors` archivés : les couleurs rouges/violettes de la planche peuvent être des plages de recoloration. Préparer les contextes de couleur/masques appropriés avant inférence ; ne pas figer ces plages dans une texture RGB universelle.31sources ne signifie pas31sorties runtime finales. L'absence de tag n'exclut pas une teinte moteur.
- Alpha : palette/indice transparent natifs, encodages normal/lumineux séparés ; les fonds noirs opaques de la planche ne préjugent pas du mélange ingame. Ni clé noire globale, ni retrait/flou universel ; conserver les petits traits des flèches, glyphes et toiles. Le sigma4 validé SPDEATH3 ne s'applique pas automatiquement.
- Exclusions : masques entièrement noirs (SHAREAB/SHGLYPH/SHSKULL/SPSDIMSP/SPSDRABU/SPSDRAE2/SPSHADOW/TRAVELB), icônes statiques, sources sans usage visuel établi, animations/décors d'autres domaines. DUST a des références ARE mais reste hors cette cohorte.
- [Planche native](preview/native.png), [périmètre/preuves](batch.json), [audit des doublons](native-duplicate-audit.json). Reproduction : `python -B pipeline/recipes/effects-next-projectiles-proposal-20261018-v1/propose.py` ; nouveau dossier si périmètre changé.
- **Proposition seulement** : aucune inférence, production, QA, installation ou release modifiée.
