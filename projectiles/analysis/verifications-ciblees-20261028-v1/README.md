# Vérifications ciblées — 2026-10-28

- Lecture seule, recette `check.py`, mesures `summary.json`, échantillons `physical-samples.json`, matrice `targeted-tests.json`. Aucun traitement IA, changement runtime ou release.
- Continuité : 243PRO actifs conformes octet pour octet à l'audit complet ; manifeste537 et registre identiques ; DLL V3 conforme au reçu. 13ressources choisies,13carriers BAM et39textures échantillonnées (9178624octets) : aucun écart SHA/taille. Ne pas extrapoler cet échantillon à un nouveau contrôle intégral des21207textures déjà vérifiées dans l'audit antérieur.
- Les6SPL actifs et tous leurs champs projectile correspondent aux usages/sourceSHA de l'analyse. Commandes ci-dessous vérifiées sur les ressources locales, aucun sort exécuté par l'agent.
- Boule de feu : preuve runtime V3 déjà acquise pour vol/FIREBAT, fumée et masques ; `../boule-de-feu-retest-v3-20261028-v1/`.
- Manques toujours présents : sorties HD BGLRYU/SPCL236U/SPGLYPHI absentes (4PRO), MAGMIS absent pour LIGHTSTO, cycle9 SPCHLGT3 non déclaré (cycles0–8 présents), SHAREA absent de la whitelist secondaire (variantes de palette enfants197–202 non finalisées), surfaces multicellules encore natives. Ces cas ne deviennent pas validés par la réussite des tests suivants.

## Test ingame ciblé

Partie de test, deux personnages éloignés ; sorts réels infligeant leurs effets. Lancer séparément ; laisser finir les nuages. Si possible refaire une fois le même sort pour distinguer premier chargement et cache chaud. Observer vol, impact, ombre, transparence et découpe près d'un élément de décor ; pause/reprise sur un effet persistant. Ne pas enregistrer cette partie de test.

| Sort | Commande | Chemin à vérifier |
|---|---|---|
| Nuage mortel | `C:Eval('ForceSpellRES("SPWI502",Player2)',0)` | Nuage persistant/SPCLOUDK, palette, transparence, fumée |
| Piège à crâne | `C:Eval('ForceSpellRES("SPWI313",Player2)',0)` | Vol/SKLT, ombre, déclenchement et fragments/SKLH ; attendre le déclenchement effectif |
| Orbe chromatique | `C:Eval('ForceSpellRES("SPWI118",Player2)',0)` | Composition primaire+ombre/SPCHRORB ; repli natif connu, test diagnostic sans présumer sa résolution |
| Fléau d'insectes | `C:Eval('ForceSpellRES("SPPR517",Player2)',0)` | X26PLAA/XIPLAUIN, vol/impact/anneau, continuité et couleurs |
| Tempête de glace | `C:Eval('ForceSpellRES("SPWI404",Player2)',0)` | FIREBALL:3 et enfants natifs ; ne pas inférer les fragments depuis la couverture du BAM primaire |
| Éclairs en chaîne | `C:Eval('ForceSpellRES("SPWI615",Player2)',0)` | Traînées SPCHLGT1/2/3 ; cible9 absente déjà connue ; besoin de cibles valides pour observer les rebonds |

- Collecter ensuite une nouvelle session de logs : étapes registre/timeline, liaisonx4, masque0x20, repli masque0x40/`EFX_MASK_FALLBACK`, erreurs de géométrie et chargement. `EFX_BOUND_PHASE` détaillé existe actuellement seulement pour FIREBAT/SPSMPUFF ; ne pas prétendre mesurer les phases finales des autres ressources depuis une simple étape0x8.
- Retour visuel utile par sort : aspect, ombre, transparence, phases manquantes/saccade, bord de décor. Un test non déclenché ne vaut pas validation négative/positive.
- Ne pas promouvoir les124cas initiaux ni l'ensemble243 à partir de ces6tests ; validation par chemin observé et limites conservées.
