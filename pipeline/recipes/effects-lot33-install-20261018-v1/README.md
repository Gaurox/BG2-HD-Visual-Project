# Lot33 — installation pour QA2026-10-18

```powershell
python -B pipeline/recipes/effects-lot33-install-20261018-v1/install.py prepare
python -B pipeline/recipes/effects-lot33-install-20261018-v1/install.py install
# Jeu/InfinityLoader fermés ; restauration limitée à cette transaction :
python -B pipeline/recipes/effects-lot33-install-20261018-v1/install.py restore
```

- Entrée scellée : `effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1/` ;33productions/36codes/5244phases/182profils,7Bx4/Apollo30, doublons retirés/durées natives conservées.
- Réemploi constructeur lot58 et transaction atomique canonique ; ajout sparse aux253RESREF existants, anciens enregistrements/backings conservés.36noms natifs prémultipliés +33alias droits `X33N01..33` ;322RESREF cumulés. Alias BURNHAND/SPPRISM3/SPPRISMT sans inférence distincte.
- Pas de modification RGB/alpha des runs ni de suppression du noir. [Audit préalable](../../../effects/research/lot33-transparency-20261017-v1/REPORT.md) :20sources avec pixels presque noirs opaques, aucun alpha gradué perdu. Les encodages et flags du test sont explicitement associés.
-33VVC `Z33T01..33` : mêmes profils par défaut que galerie8789 ; feu/froid/lumière/SPHORPUF en Blended, autres fumées/matières/sang en normal. Choix de test par famille, **pas un relevé des flags natifs**.182VVC `Z33P0001..0182` : tous cycles/modes ;66VVC `Z33B01..33` /`Z33N01..33` : comparaison explicite lumineuse/normale. Sans gameplay, boucles bornées à au moins4s.
- Les tests VVC utilisent le contexte d'effet déjà pris en charge. Une présence correcte via ces CLUA ne prouve pas le remplacement HD ou le mélange sur les chemins natifs directs des vrais sorts. Owner/tint/cadence réelle demeurent à observer ; aucune QA acquise.
- Vérification candidate/installée : probe catalogue natif existant, budget32Mio de l'INI actuel ; contrats anciens70888 +nouveaux. Aucun rebuild de DLL ; DLL/INI/shaders/profil personnages/exécutable hashés avant/après et inchangés.
- `effects/installations/lot33-native-impacts-20261018-v1/` : `before.json`, `plan.json`, candidat local ignoré, `transaction.json`, `installation.json`,33CLUA,182profils,66comparaisons. Transaction refuse les collisions de nouvelles cibles et vérifie jeu+InfinityLoader fermés ; sauvegarde des deux autorités remplacées, rollback ciblé sur échec. Suivi installation seul ; QA/release indépendantes.
- `finish` récupère l'enregistrement métier après une transaction `installed` déjà vérifiée, sans recopier. `restore` rétablit les octets et les deux colonnes d'installation des lignes encore liées à ce reçu ; `restoration.json` porte l'état ultérieur, reçu d'installation conservé.
