# Menus BG2EE — méthode actuelle

Variante active : `../x4-topaz-recovery-v2-d50/`. Les anciennes comparaisons SeedVR, AdaIN, x2
et xBR sont isolées sous `../archive/variants/` et ne doivent pas guider une nouvelle production.

## Contrat

- Topaz Gigapixel Recovery v2, Detail 50, x4, couleurs préservées.
- Extraire et traiter chaque élément BAM/MOS séparément.
- Ne jamais upscaler un atlas complet : les éléments voisins contamineraient leurs bords.
- Recomposer les pages DXT5 sans changer la géométrie BAM/MOS logique.
- Garder taille, format et empreinte FNV-1a de chaque page dans le registre moteur.
- Installer et restaurer avec les scripts de la variante, jeu et InfinityLoader fermés.

## Séquence

1. Identifier les pages et éléments dans `reference/` et les manifests de la variante active.
2. Extraire la source native sans l'écraser.
3. Produire un fichier x4 par élément avec le preset validé.
4. Reconstruire les atlas via le builder de `x4-topaz-recovery-v2-d50/`.
5. Vérifier dimensions x4, format DXT5 et inventaire exact.
6. Installer transactionnellement ; vérifier les clés `[Shaders]` documentées dans
   [`../../README.md`](../../README.md).
7. Lancer `InfinityLoader.exe`, contrôler une ligne `Replacing MOS...` par page et effectuer la QA
   visuelle.

## Gate

La variante courante doit être reconstruisible sans fichier d'une variante archivée. Une nouvelle
variante reste expérimentale jusqu'à comparaison contrôlée, install/restore réussi et acceptation
utilisateur. Elle ne remplace pas la variante active par simple présence dans l'arborescence.
