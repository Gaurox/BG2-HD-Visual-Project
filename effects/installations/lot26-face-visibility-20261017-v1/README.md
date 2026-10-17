# OHRFEAR corrigé + tests09/26 décalés

- Retour ultérieur :09/26visibles avec décalage,12corrigé, **26/26 acceptés ingame** ; [décision finale](../../batches/lot26-accepted-20261017-v1/acceptance.json), [CLUA validées](../../batches/lot26-accepted-20261017-v1/CLUA.md). Reçu technique historique inchangé.

- Installé jeu/InfinityLoader fermés ; `transaction.json`,93cibles sauvegardées/copiées/hashées.90RGBA OHRFEAR remplacés, manifest mis à jour,2VVC ajoutés ; registre/carrier/DLL/INI/shaders/personnages inchangés.252autres ressources et leurs frames identiques.
- ManifestSHA256 `44A63CBDDC7609D9C89921C0BEBE148A577847AB28D2B400DB8AEDF91C34E924`. Catalogue253RESREF/32927backings ;70888contrats natifs passent candidat+installation, zéro lecture RGBA par la sonde catalogue.
- 12 : trou central du visage comblé avant feather12,90phases/durée3s conservées ; contour extérieur et RGB existants inchangés. [Production](../../batches/ohrfear-face-fill-20261017-v1/README.md).
- 09/26 : nouveaux contrôleurs décalés X=64 pour isoler un possible masquage par le personnage ; cycle/blend/alpha/durée identiques aux tests d’origine, aucun changement des vrais effets09/26. Visibilité confirmée par utilisateur avec décalage ; mécanisme précis non mesuré.
- Lancer via InfinityLoader ; une commande à la fois :

```lua
-- 09 TRVENTAA : contrôle décalé, cycle002-once,0.6s
C:Eval('CreateVisualEffectObject("Z26V09",Player1)',0)
-- 26 TRSPEART : contrôle décalé, cycle000-once,16/15s
C:Eval('CreateVisualEffectObject("Z26V26",Player1)',0)
-- 12 OHRFEAR : même commande, trou corrigé
C:Eval('CreateVisualEffectObject("Z26T12",Player1)',0)
```

- Les [26commandes initiales](../lot26-sdf-no-inset-20261017-v1/CLUA.md) restent installées. QA/release indépendantes, aucune acceptation déduite.
- Restauration ciblée : `python -B pipeline/recipes/effects-lot26-face-visibility-20261017-v1/repair.py restore`, jeu/InfinityLoader fermés. Réconcilier ensuite l’état d’installation CSV ; ancien reçu/production conservés.
