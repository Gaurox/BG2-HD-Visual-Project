# Production rapide et finalisation

## Doctrine

Pendant la production, traiter et accepter des assets autonomes. Ne pas reconstruire ni prouver le
projet global. Compiler, revalider et optimiser l'ensemble uniquement pendant une finalisation
explicitement demandée.

## Deux modes exclusifs

| Mode | But | Contrôles | Écritures |
|---|---|---|---|
| Production rapide (défaut) | Ajouter un asset final | risque local + QA utile | run retenu + petite autorité métier/candidat |
| Finalisation | Produire une distribution | registres, hashes physiques, staging, moteur, installateur | projections, TP2, miroirs, payload, archive |

Une commande de production ne doit pas déclencher implicitement une finalisation.

## Voie quotidienne

1. Produire ou corriger l'asset dans son domaine.
2. Utiliser les invariants intégrés au producteur ; lancer un contrôle ciblé seulement s'il révèle
   un risque encore inconnu.
3. Installer/restaurer transactionnellement si une QA ingame est utile.
4. Après décision utilisateur, sceller le résultat retenu et ajouter son enregistrement candidat.
5. S'arrêter. Ne pas régénérer `asset-tracking/*`, `content.json`, `components.json`, le TP2, les
   miroirs package, le staging ou une archive.

## États opérationnels

| État | Sens |
|---|---|
| `working` | essai mutable ou jetable ; aucune garantie de conservation |
| `accepted` | résultat exact retenu, QA explicite si nécessaire, autorité candidate mise à jour |
| `packaged` | dérivé de finalisation ; jamais maintenu asset par asset |

Les anciens états plus détaillés restent lisibles pour compatibilité. Ils ne créent aucune étape
supplémentaire dans la voie quotidienne. Installation, projection et présence dans un payload ne
sont pas des conditions pour enregistrer `accepted`.

## Conservation

- Immuable : source native, résultat `accepted`, décision QA finale, manifeste qui les relie.
- Jetable : previews, plans, thumbnails, staging, projections globales, essais refusés sans valeur
  diagnostique unique.
- Un essai refusé n'est conservé que s'il documente une limite réutilisable ; conserver alors la
  recette et la conclusion, pas nécessairement tous les médias.

## Contrôles locaux irréductibles

- identité/resref et frontière du domaine ;
- dimensions, format, inventaire et géométrie nécessaires au moteur ;
- fermeture du jeu et d'InfinityLoader avant remplacement ;
- installation/restauration transactionnelle ;
- décision QA explicite avant `accepted` lorsqu'elle est visuelle ;
- aucun hash global pendant l'acceptation quotidienne.

Les hashes physiques et la présence complète sont calculés une fois pendant la finalisation.

## Finalisation explicite

Ordre unique : compiler les candidats acceptés → générer les manifestes/TP2 → rehash physique
global → staging → tests release/moteur/installateur → optimisation → archive. Les documents sous
`releases/BG2-HD-Upscale/docs/` décrivent ce mode uniquement.

```powershell
& releases/BG2-HD-Upscale/tools/Compile-BG2HD-Release.ps1
& releases/BG2-HD-Upscale/tools/Test-BG2HD-Phase2.ps1
```

## Statut des documents

| Type | Effet normatif |
|---|---|
| Politique (`AGENTS.md`, ce fichier) | règles communes minimales |
| README de domaine | voie rapide et autorités |
| Recette | consultée seulement pour son symptôme/format |
| Finalisation | ignorée hors demande de release/package |
| Historique/audit daté | mémoire ; aucune obligation courante |

Une recette ne peut pas introduire un rituel global. Les mots « obligatoire », « gate » et « avant
toute » sont réservés aux garde-fous locaux ci-dessus ou à la finalisation.
