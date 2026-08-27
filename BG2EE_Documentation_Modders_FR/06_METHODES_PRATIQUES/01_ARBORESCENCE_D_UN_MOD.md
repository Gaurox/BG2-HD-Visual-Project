# Arborescence recommandée pour un mod technique

> **Statut :** Synthèse pratique  
> **Dernière vérification :** 2026-08-27

## Exemple

```text
mon_mod/
  README.md
  CHANGELOG.md
  LICENSES/
  docs/
  setup-mon_mod.tp2
  mon_mod/
    lib/
    tra/
    scripts/
    data/
    ui/
    sprites/
    manifests/
    tools/
    tests/
  dist/
```

## Règles

- ne pas mélanger sources et fichiers générés ;
- ne pas versionner les caches temporaires ;
- conserver un manifeste machine-lisible des ressources finales ;
- placer les outils de conversion dans un dossier séparé ;
- documenter les versions des dépendances ;
- produire `dist` depuis une commande reproductible.

## Pour un pipeline de sprites

```text
sprites/
  source_originale/
  extraction/
  upscale_x2/
  upscale_x4/
  reconstruction/
  validation/
```

Les sorties x2 et x4 doivent provenir de la même source originale et rester séparées. Les corrections manuelles doivent être enregistrées comme données ou patchs reproductibles, pas appliquées uniquement sur une copie finale.

## Pour l’interface

Séparer :

- fichiers `M_*.lua` ;
- patchs `UI.menu` ;
- images/polices ;
- tests de compatibilité ;
- snapshots des versions de base prises en charge.
