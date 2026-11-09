# Avancement des validations projectiles — 2026-11-10

- **Réconciliation courante : [résultat et exceptions](analysis/owner-contracts-20261110-v1/README.md)** ; autorité machine `index/owner-reconciliation-current.json`, liens individuels `index/work-tracking.json:integration.automatic_reconciliation`.
- **320 propriétaires examinés : 243 PRO +77 IDs moteur. 299 contrats compatibles ;13 IDs regroupés en4 exceptions actives ;8 écarts natifs sans pilote statique conservés séparément.** Réconciliation technique, aucune nouvelle QA visuelle globale.

| Indicateur | Compte | Avancement |
|---|---:|---:|
| Contextes graphiques explicites du suivi couverts |167 sorties réutilisables +8 masques natifs /175 |100 % côté production/disposition |
| Contrats techniques réconciliés, PRO +IDs moteur |299 /320 |93,4 % |
| Contrats techniques des PRO seuls |242 /243 |99,6 % |

- Les175 contextes sont des variantes source/palette de107 BAM explicites, pas175 PRO. Les branches moteur réemploient aussi des images déjà produites dans les autres domaines ;leurs exceptions sont comptées séparément ci-dessous.
- QA visuelle directe :39 PRO +10 IDs,portées observées seulement. Aucun pourcentage global de chaînes visuellement validées ne peut être déduit de ces compteurs ;le réemploi technique évite les tests manuels répétés.

| Domaine | Acquis / disposition courante |
|---|---|
| Source |243 PRO,107 BAM explicites,175 contextes source/palette. Op140/op141 :1 400 références ajoutées ;60 IDs moteur avec pilotes statiques contre33 dans l'ancien scan capacités/enfants. |
| Production |167 contextes réutilisables (86 acceptés +81 packs palette vérifiés),8 masques natifs ;0 nouvelle inférence identifiée. Les images des4 exceptions existent déjà. |
| Contrats par propriétaire |242 PRO +57 IDs réconciliés ;31 668 contrats cycles/slots/phases/base/once/dimensions/centres passants au chargeur natif ;0 modification PRO inexpliquée. |
| Octets installés concernés |25 017 backings /13,08 Go couverts SHA,0 écart ;carriers natifs conformes. Registre743 ressources /72 563 backings inchangé. |
| QA visuelle |39 PRO +10 IDs acceptés dans leurs portées observées ;QA images et preuves communes reliées sans élargir les décisions. Les3 couleurs HLYMITE rouge194/SHAIR4/SHEARTH6 restent acceptées ;0 test manuel en attente. |
| Raccords précédents |10/10 omissions initiales installées ;6 routes +3 couleurs observéesHD. SPSCORIC :9 cycles qualifiés,QA antérieure conservée ;pas de nouveau drawlive revendiqué. |
| Runtime / release |DLL `5A1559B5…3106612B`,trace désactivée ;aucune nouvelle installation,compilation,image ou release modifiée par la réconciliation. |

## Exceptions à traiter

| Famille | Écart | Suite technique |
|---|---|---|
| SHWATER —8 IDs | Cellule SpellHit hors scope ;7 palettes BMP sans transfertHD | Raccord +palette réalisée par cellule ;réemploi des images. |
| FLMSTRK —ID145 | Route SkyStrike hors scope ;pilote op141 retrouvé | Raccorder le pack existant ;ID66 partage l'image sans pilote dans le scan. |
| SPDIMDR1/2 —ID109 | Deux phases natives hors scope ;17 références op141 | Raccord des2 packs etqualification du cycle de vie2→1→2. |
| SPBOOM —IDs142/143/144 | Recolorations MPALETTE67/65/69 non transférées | Qualifier/appliquer ces3 couleurs ;QA neutre/Fireball acquise inchangée. |

- Détails/sources/offsets : [exceptions.json](analysis/owner-contracts-20261110-v1/exceptions.json), [opcodes](analysis/owner-contracts-20261110-v1/opcode-references.csv). Aucun CLUA supplémentaire demandé à ce stade.
- Écarts sans pilote scanné : LIGHTSTO/MAGMIS,SPBRNHND,SPSMKJET,COLRSPRY,SPHOLYMT —8 propriétaires,5 familles ;conserver natif,sans production ni essai spéculatif. Absence de référence statique ≠inutilisation universelle.
- Aucun défaut supplémentaire de géométrie/cycle/registre/palette de PRO connu après rapprochement. Ombres natives,VVC SHAREAW,contrôleurs sans image et périodes LIGHTCHA réconciliés sans retest.
- Déplacement interpolé `PROJ-MOTION-001` reporté ;release distincte. Aucun pourcentage de chaînes gameplay intégralement acceptées déduit.

## Lecture des anciens compteurs

- Les161 «réemplois à vérifier»,54 «routes moteur à résoudre»,27 «natifs à examiner» du générateur source sont une projection conservatrice historique ;**la liste active est désormais réduite aux4 familles ci-dessus**.
- Une QA `not-assessed` reste une absence de décision visuelle individuelle ;elle ne signifie ni contrat cassé ni test à imposer. L'état technique réconcilié est enregistré séparément,sans écraser QA/installation/release.
