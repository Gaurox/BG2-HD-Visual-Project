# MFIE7314 — palettes natives G1/G2, correction installée

- Scope : `0x7314 BURNING_MAN`, Q3m V7 K6/quatre partenaires/huit niveaux/x2/Nearest sans SDF. Autorisation utilisateur : « gpu libre go ». Production + installation terminées ; **QA MFIE ingame en attente**. Aucun commit/release dans cette reprise.
- Parent actif : `../q3m-mfie-palette-stability-x2-20261007-v2/current-generation.json`. Autres 330 IDs/63 015 routes/composants identiques ; 76 décisions Monster acquises conservées, aucune validation inférée.

## Cause vérifiée

- Session `2026-10-07 01:08:06.700` : MFIEG12 chargé ; `MFIE_PALETTE entries=253 accepted=false crc32=0947181D`. [Trace](session-evidence.txt), [analyse scellée](analysis.json).
- Palette live G1 : `MFIEG31`, 253 entrées ; préfixe RGB exact. Ancienne production : `MFIEG3B`, 252 entrées, 209 différences RGB → refus natif justifié, rendu vanilla.
- [Code natif](native-bank-selection.txt), EXE `b51093a4…` : SetSequence G1 sélectionne `this+0x124C palette1` RVA `0x3399A8` ; G2 sélectionne `this+0x1254 palette2` RVA `0x339176` ; liaison bitmap commune `0x3399BC`. MonsterRender lit la palette du bitmap `0x32DA8F`.
- Contrat correct : G1→MFIEG31/253, G2→MFIEG3B/252, INV→palette BAM propre. `general.new_palette` seul ne décrit pas les palettes effectivement sélectionnées par groupe natif.

## Production et runtime

- [Sélection](selection.json)/[plan](plan.json) : 14 ressources, 5 888 frames, 921 travaux source/922 encodages ; 381 hits acquis SHA inchangés ; 541 manquants =540 guides/3 240 cibles K6/540 encodages +1 spécial sans GPU. [Encodage](encoding.json), [production](production.json).
- Six feuilles G1 changées : `MFIEG1`, `MFIEG11`, `MFIEG12`, `MFIEG13`, `MFIEG14`, `MFIEG15`. G2/21–26 +INV : huit feuilles identiques au parent. Aucun sprite spatial multipart dans ce delta.
- Pipeline `pipeline/scripts/q3m_family_witnesses.py` : sous-ensemble explicite `animation_ids=['0x7314']` ; sélection Monster des palettes INI `palette1/2` par banque, support MultiNew acquis conservé. La sélection complète reste le défaut.
- DLL construite depuis le snapshot **installé v2** ; seul `src/iee/creature_sprite_x2.cpp` change. [Runtime/provenance](runtime.json), [delta](runtime-delta.patch). Hooks/attente Monster/Loop-Clamp natifs acquis inchangés ; aucune réintroduction des essais Character en stock.
- Garde strict MFIE/kind0/G1-G2 : compte natif 253/252 ou256 avec queue inexistante sans dépendance I/F ; comparer chaque RGB utile/alpha0 ou255. Mauvais compte/palette/type rejeté ; autres IDs inchangés. Trace MFIE_PALETTE bornée conservée.

## Vérifications et installation

- [Vérification](verification.json) : 14 ressources/5 888 frames K6×3 formats, 758 810 088 pixels décodés ; 9 741 slots natifs. Gardes : 64 746 cas, 16 852 contrôles de lecture native, 766 cycles, zéro frame manquante/erronée. Toutes les 5 886 frames monde portent la palette BMP exacte et aucune dépendance hors entrées natives.
- [Catalogue](catalog-proof.json) : seul7314 remplacé ; 330 IDs/63 015 routes/digests exacts. Actif : 331 IDs/14 330 feuilles/2 791 737 frames. Feuilles historiques non supprimées.
- DLL SHA256 : `c8690b4edd978d28eafabd1e6aafbd2533820c0bfbc0ea88192ea161850e5697`.
- Catalogue SHA256 : `d013ac44d8925cbaa972f15697e1e6b49d4230e1f09747bb11779a63c56f2ff6`.
- [Génération installée](current-generation.json) = famille77IDs +delta7314 ; [production composite](production-generation.json) = production complète parent +delta, indépendante de QA/installation.
- `install.ps1 -DryRun` puis installation autorisée, jeu/InfinityLoader fermés. Six feuilles nouvelles ; DLL/catalogue remplacés avec sauvegarde de la paire parent ; 1 119 fichiers SHA conservés (anciennes feuilles Monster/77CRE/INI/shaders/EXE). [Preuve copie](installation-verification.json), [contre-vérification](installed-verification.json).
- Reçu actif : `ingame-installation/active-test.json`. Restauration locale : `restore.ps1 -DryRun`, puis `restore.ps1` ; ancien couple DLL/catalogue restauré, uniquement six feuilles identifiées v3 retirées. Après restauration volontaire, réconcilier les pointeurs actifs de suivi.
- Travail local : `sprite/.work/q3m-mfie-native-palettes-x2-20261007-v3/{isolated,combined,runtime-src,runtime-build}`. Artefacts/proofs antérieurs immuables.

## QA restante / constat supplémentaire

```lua
C:CreateCreature("QMON7314")
```

- Retest MFIE : apparence initiale, mouvement/sélection et attaque G2 ; compte courant76/77, aucune QA automatique.
- [Audit additionnel en lecture seule](other-bank-audit.json) : `7312 BLUE_FIRE`/`7313 MFIS` ont des palettes G1/G2 différentes ; leurs feuilles G2 utilisent encore G1. Respectivement236/253 différences RGB. Risque de refus sur G2, **aucun échec ingame constaté pour ces deux IDs**. Sprites et QA historiques conservés ; observation séparée des attaques `QMON7312`/`QMON7313` utile, pas de régénération silencieuse.

## Scripts de reproduction

- `prepare.py` : session/palettes/code natif +plan ; `build_runtime.py` : fork snapshotv2/delta/build ; `produce.py` : cache exclusif +GPU +pack ; `prepare_install.py` : remplacement7314 et preuve330IDs ; `verify.py` : gardes/lectures/pixels natifs ; `other_bank_audit.py` : constat additionnel ; `finish.py` : copie réelle +suivi.
- Scripts à sorties finales scellées : ne pas relancer en écrasant une preuve historique ; nouvelle version si remplacement nécessaire. Tests/QA/installations non déduits les uns des autres.
