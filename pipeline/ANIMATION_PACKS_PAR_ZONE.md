# Packs d'animations par zone — runbook agent

## Routage

Utiliser ce document pour **découper un pack d'animations terminé en un pack par zone**, puis
l'installer. C'est la voie normale dès qu'un pack global dépasserait 512 MiB.

Ne pas utiliser cette voie :

- pour produire le x4 spatial : [`ANIMATION_UPSCALE_PIPELINE.md`](ANIMATION_UPSCALE_PIPELINE.md) ;
- pour produire le 30 fps : [`ANIMATION_UPSCALE_30FPS_V2.md`](ANIMATION_UPSCALE_30FPS_V2.md) ;
- pour remplacer les répétitions d'un cycle :
  [`ANIMATION_INTERPOLATION_PIPELINE.md`](ANIMATION_INTERPOLATION_PIPELINE.md).
- pour donner des masques distincts à plusieurs occurrences d'un même resref :
  [`ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](ANIMATION_PER_OCCURRENCE_OCCLUSION.md).

Scripts : `pipeline/scripts/split_animation_pack_by_area.py`,
`pipeline/scripts/Install-AreaAnimations-PerArea.ps1`,
`pipeline/scripts/Restore-AreaAnimations-PerArea.ps1`.

## Pourquoi

Le moteur ne charge qu'un seul `AreaAnimations-X4.registry`, et sa charge RGBA brute est plafonnée
à 512 MiB (`kMaxRawBytes`, `area_animation_x4_registry.cpp`). **Ce budget est cumulatif sur toutes
les zones déjà converties et ne redescend jamais** : chaque zone traitée ampute la marge de toutes
les suivantes.

Mesuré sur les index du projet : l'inventaire complet représente ~2,7 GiB en x4 natif et
~5,5 à 8 GiB une fois interpolé, soit 11 à 16 fois le plafond. Un pack global ne peut donc pas
couvrir le jeu, quel que soit l'ordre de traitement.

Découpé par zone, le plafond devient une limite **par zone** : sur 236 zones porteuses
d'animations, 234 tiennent seules sous 512 MiB même au coût 30 fps le plus défavorable, et la zone
médiane pèse 15 MiB (3 % du plafond).

Les deux exceptions se traitent au cas par cas, en laissant leurs ressources les plus lourdes en
x4 natif : `OH8100` (dont `BDFORCEW`, 160 frames, fait à elle seule 370 des 375 MiB) et `AR2300`
(12 cascades `FALL*`).

## Contrat fixe

- Entrée : un pack terminé, registre v1, v2 ou v3, validé par son propre manifeste.
- Sortie : un dossier par zone, chacun un pack registre v3 complet et autonome
  (`AreaAnimations-X4.registry` + ses `AAX4-*.rgba` + `manifest.json`), plus un index à la racine.
- Une zone reçoit un pack **seulement** si elle pose au moins une ressource présente dans le pack
  source. Les autres n'en ont pas et le moteur y affiche ses BAM d'origine.
- Les ressources partagées sont **dupliquées** dans chaque zone utilisatrice : c'est ce qui rend
  chaque pack indépendamment chargeable et vérifiable. Surcoût disque mesuré : ×1,47.
- Plusieurs variantes d'un même resref sont toutes conservées dans la zone. Leurs positions et
  `variant_index` ne doivent jamais être rabattus dans un dictionnaire indexé par le seul resref.
- L'appartenance zone → resref vient d'`animations/index/occurrences.csv`, jamais d'un nom de
  dossier ; l'empreinte de cet index est inscrite dans la sortie.
- Chaque pack de zone est soumis au plafond de 512 MiB. L'index liste `areas_over_budget` et
  l'installateur refuse d'installer si cette liste n'est pas vide.
- Le script ne modifie jamais le jeu, la DLL, l'INI, `override`, le pack source ni les catalogues.

## Étape 1 — découpage

```powershell
python pipeline/scripts/split_animation_pack_by_area.py `
  --pack <pack-termine>/03_runtime_pack `
  --output animations/packs-par-zone/<lot>
```

Contrôler dans l'index produit (`<output>/manifest.json`) :

```text
areas_over_budget      = []           # sinon : ne pas installer, alléger les zones citées
area_count             = nombre de zones réellement servies
largest_area_raw_bytes < 536 870 912
resrefs_without_area   = []           # sinon : ressource convertie que personne ne pose
```

Rejouer la même commande avec `--resume` revalide sans réécrire.

## Étape 2 — préflight d'installation

Jeu et `InfinityLoader` fermés :

```powershell
.\pipeline\scripts\Install-AreaAnimations-PerArea.ps1 `
  -SplitRoot animations\packs-par-zone\<lot> `
  -VerifyOnly
```

Le préflight revalide **chaque** pack de zone (manifeste, registre, taille et SHA-256 de chaque
asset) avant toute écriture. Il refuse : un pack d'auteur non découpé
(`runtime_budget_enforced: false`), une zone au-delà du budget, un identifiant de zone non
alphanumérique, un asset absent ou divergent.

## Étape 3 — installation

Ne franchir ce gate que si la demande utilisateur autorise l'installation.

```powershell
.\pipeline\scripts\Install-AreaAnimations-PerArea.ps1 `
  -SplitRoot animations\packs-par-zone\<lot>
```

L'installateur sauvegarde DLL, INI et le dossier `areas` existant, installe la DLL et
`iee-assets\areas\<ZONE>\`, force `EnableAreaAnimationX4=true` sous `[Shaders]`, puis revérifie
tous les hashes. Il ne lance pas le jeu. Conserver le chemin `per-area-backup-*` affiché.

Le registre global historique reste en place mais devient **inerte** dès que `iee-assets\areas`
existe : il n'est ni supprimé ni modifié.

## Étape 4 — QA en jeu

Vérifier, en plus de la matrice habituelle du 30 fps :

1. l'animation s'affiche dans une zone servie par un pack ;
2. **changement de zone puis retour** — c'est le chemin nouveau, il déclenche le rechargement ;
3. une zone **sans** pack affiche ses BAM d'origine sans artefact ;
4. plusieurs allers-retours d'affilée entre deux zones servies, pour vérifier qu'aucune texture
   n'est perdue ni dupliquée ;
5. pause/reprise et sortie/retour dans le champ, comme pour un pack global.

Le journal du moteur trace chaque bascule : `per-area packs enabled from ...` au démarrage, puis
`Prepared area-animation x4 runtime pack ...` par zone servie, ou `no pack for area <ZONE>` sinon.

Commande de téléportation à donner à l'utilisateur, une par zone :

```
C:MoveToArea("AR0603")
```

## Restauration

```powershell
.\pipeline\scripts\Restore-AreaAnimations-PerArea.ps1 -BackupPath <per-area-backup> -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimations-PerArea.ps1 -BackupPath <per-area-backup>
```

Remet DLL et INI, et rétablit `areas` à l'identique — réinstallé s'il existait, supprimé sinon.

## Ce que fait le moteur

- `configure_area_packs()` au démarrage : si `iee-assets\areas` existe, le mode par zone s'active
  et **rien** n'est chargé à ce moment. Sinon le pack global unique est chargé comme avant.
- `prepare_for_area()` depuis le hook `LoadArea`, après l'appel original : résout le resref de la
  zone active, charge `areas\<ZONE>\`, ou relâche tout si la zone n'a pas de pack.
- Une zone déjà résidente n'est pas rechargée.
- `LoadArea` ne touche jamais à OpenGL : les textures sortantes sont **parquées**, puis rendues au
  moteur par `flush_retired_textures()` à la passe Seam suivante. Sans cela chaque transition
  abandonnerait jusqu'à 64 noms de texture.
- Un contexte GL recréé invalide les noms parqués : ils sont alors abandonnés sans suppression,
  jamais supprimés dans un autre contexte.

## Conditions d'arrêt

- `areas_over_budget` non vide → alléger les zones citées avant tout autre pas.
- Préflight en échec → arrêter ; ne pas copier à la main ni supprimer une zone pour passer.
- QA refusée → restaurer, conserver le lot refusé, repartir d'un nouveau découpage.
- Ne jamais supprimer un pack source, un lot découpé refusé ou une sauvegarde.
