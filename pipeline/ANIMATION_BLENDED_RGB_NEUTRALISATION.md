# Animations « Blended » — neutralisation RGB sous alpha nul

## Routage

Utiliser ce document quand une animation de zone upscalée xN présente **un fond, un halo, un
voile ou un rectangle visible autour du sujet, absent en vanilla**.

Ne pas utiliser cette voie :

- pour un liseré, un escalier de contour ou un bord de canvas sur une ressource **non Blended** :
  [`ANIMATION_ALPHA_CORRECTIONS.md`](ANIMATION_ALPHA_CORRECTIONS.md) ;
- pour un défaut situé **à l'intérieur** du masque alpha : voir « Contre-exemple » plus bas ;
- pour l'occlusion par un élément de décor :
  [`ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](ANIMATION_PER_OCCURRENCE_OCCLUSION.md).

Script : `pipeline/scripts/build_blended_rgb_neutral_pack.py`.

## Gate d'entrée — obligatoire avant toute correction alpha

**Avant de proposer un feather, un masque ou un seuil sur l'alpha d'une animation, exécuter les
deux tests ci-dessous.** S'ils sont positifs, une correction côté alpha est **structurellement
incapable** de retirer le défaut : `ANIMATION_ALPHA_CORRECTIONS.md` préserve le RGB octet pour
octet et ne couvre pas cette classe.

Signal comportemental qui doit déclencher ces tests immédiatement : **des corrections alpha de
plus en plus agressives ne changent rien ou presque rien en jeu.**

### Test 1 — flag ARE bit 1 « Blended »

```powershell
python -c "import csv,collections; f=collections.defaultdict(set); [f[r['resource_resref']].add(int(r['flags_hex'],16)) for r in csv.DictReader(open('animations/index/occurrences.csv'))]; rr='<RESREF>'; print(rr,[hex(x) for x in sorted(f[rr])],'blended' if any(x>>1&1 for x in f[rr]) else 'alpha strict')"
```

`bit 1` (`0x0002`) mis sur au moins une occurrence ⇒ la ressource est rendue par le chemin
blended.

### Test 2 — couleur sous alpha nul dans le pack

```powershell
python -c "import numpy as np,json; pk=r'<PACK_OU_ZONE>'; m=json.load(open(pk+'/manifest.json')); r=[x for x in m['resources'] if x['resref']=='<RESREF>'][0]; f=r['frames'][<INDEX>]; w,h=f['physical_size_x4']; a=np.frombuffer(open(pk+'/'+f['asset'],'rb').read(),np.uint8).reshape(h,w,4); o=a[:,:,3]==0; print('texels alpha==0:',int(o.sum()),'| dont colores:',int((o&(a[:,:,:3].sum(2)>0)).sum()),'| luminance max:',float(a[:,:,:3].mean(2)[o].max()))"
```

Texels colorés > 0 avec une luminance max notable (dizaines) ⇒ défaut confirmé.

Les deux tests positifs ⇒ appliquer ce document. Un seul positif ⇒ ne pas appliquer, rediagnostiquer.

## Cause

Le moteur ne compose pas une animation `Blended` en alpha strict : **le noir est la valeur
transparente et les canaux RGB sont additionnés à la scène**. Un texel à `alpha == 0` apporte
donc quand même sa couleur.

Le BAM x1 n'en souffre pas : le compositeur CPU du moteur saute l'index transparent de la
palette. Le remplacement xN est une texture GL RGBA complète, donc **chaque texel atteint le
blend**. Le modèle d'upscale ne voit que le plan RGB, où la zone transparente est un aplat de
chroma, et il y hallucine de la structure. Cette structure devient visible à pleine force.

L'alpha n'est pas le canal qui contrôle la visibilité sur ce chemin. Le corriger ne fait rien.

## Contrat fixe

- Entrée : un split-root produit par `split_animation_pack_by_area.py`.
- Sortie : un nouveau split-root ; l'entrée n'est jamais modifiée.
- `--mode zero` : `RGB = 0` là où `alpha == 0`. **Mode par défaut, suffisant tant que l'alpha est
  strictement binaire** — ce que produit l'agrandissement nearest d'un masque BAM.
- `--mode premultiply` : `RGB = RGB * alpha / 255` partout. **Obligatoire dès que l'alpha porte
  des valeurs intermédiaires** (feather, masque peint) : sur le chemin blended un texel à demi
  transparent ajouterait sinon sa couleur pleine, et la rampe se lirait comme un halo lumineux
  au lieu d'un fondu.
- Le plan alpha est asserté **inchangé octet pour octet**.
- Le RGB **à l'intérieur** du masque est inchangé octet pour octet : aucun détail xN n'est perdu.
- L'opération est un no-op sur le chemin alpha strict (ces texels y sont jetés), donc sûre pour
  toute ressource quel que soit son flag. Ne cibler malgré tout que les resrefs diagnostiqués.
- Ne touche jamais le jeu, la DLL, l'INI, `override`, le split-root d'entrée ni les catalogues.

## Position dans la chaîne

La neutralisation s'insère **après le découpage par zone et avant les fusions de zones**, parce
que `merge_area_pack_resources.py` consomme des packs de zone déjà définitifs :

```text
run V1 x4 (et/ou V2 30 fps)
  -> merge_v2_base_pack.py            si plusieurs sources
  -> split_animation_pack_by_area.py
  -> build_blended_rgb_neutral_pack.py     <= ICI
  -> merge_area_pack_resources.py     zones deja installees qui posent aussi le resref
  -> combine_area_pack_splits.py
  -> Install-AreaAnimations-PerArea.ps1
```

Quand la ressource est ajoutée à une zone **qui sert déjà d'autres ressources**, l'ordre s'inverse :
fusionner d'abord avec `merge_v2_base_pack.py`, redécouper la zone, puis neutraliser — la
neutralisation exige un split-root en entrée, jamais un pack seul. Voir
[`ANIMATION_PACKS_PAR_ZONE.md`](ANIMATION_PACKS_PAR_ZONE.md) § « Étape 1b ».

```text
pack de zone existant + run V1 neuf
  -> merge_v2_base_pack.py
  -> split_animation_pack_by_area.py --occurrences <index restreint a la zone>
  -> build_blended_rgb_neutral_pack.py
  -> combine_area_pack_splits.py --replace-area <ZONE>
```

## Commande

```powershell
python pipeline/scripts/build_blended_rgb_neutral_pack.py `
  --split-root animations/packs-par-zone/<split-source> `
  --output animations/packs-par-zone/<split-neutralise> `
  --resref <RESREF1> --resref <RESREF2> `
  --mode zero
```

Contrôler dans la sortie :

```text
rule            = rgb=0 where alpha==0
requested_resrefs = les resrefs vises
frames_changed  > 0
pixels_changed  > 0
areas_over_budget = []
```

`frames_changed == 0` ⇒ la ressource n'avait pas de couleur sous alpha nul : le diagnostic était
faux, ne pas installer, reprendre l'analyse.

Options complémentaires, à n'utiliser que sur besoin établi :

- `--feather-proto <proto build_alpha_feather.py>` : substitue le plan alpha du prototype avant
  application de la règle. Impose `--mode premultiply`. Le `source_runtime_sha256` du prototype
  est vérifié contre l'asset qu'il prétend dériver.
- `--inner-feather-x4 <rayon>` : applique le fondu de silhouette. Impose `--mode premultiply`.
  Exclusif avec `--feather-proto`.
- `--mask-png` + `--mask-origin-x4` + `--mask-anchor-x1` : masque d'occlusion peint ancré en
  coordonnées monde, réprojeté sur chaque frame depuis son propre centre BAM, et inscrit en
  registre v3 comme position exacte de l'occurrence. Impose `--mode premultiply`.

## Vérification obligatoire avant installation

```powershell
python -c "import numpy as np,json; NEW=r'<split-neutralise>/<ZONE>'; OLD=r'<split-source>/<ZONE>'; mn=json.load(open(NEW+'/manifest.json')); mo=json.load(open(OLD+'/manifest.json')); rr='<RESREF>'; i=<INDEX>; rn=[x for x in mn['resources'] if x['resref']==rr][0]; ro=[x for x in mo['resources'] if x['resref']==rr][0]; fn,fo=rn['frames'][i],ro['frames'][i]; w,h=fn['physical_size_x4']; an=np.frombuffer(open(NEW+'/'+fn['asset'],'rb').read(),np.uint8).reshape(h,w,4); ao=np.frombuffer(open(OLD+'/'+fo['asset'],'rb').read(),np.uint8).reshape(h,w,4); out=an[:,:,3]==0; print('alpha inchange:',np.array_equal(an[:,:,3],ao[:,:,3]),'| RGB intra-masque inchange:',np.array_equal(an[:,:,:3][~out],ao[:,:,:3][~out]),'| RGB colore hors masque:',int((out&(an[:,:,:3].sum(2)>0)).sum()),'(avant',int((out&(ao[:,:,:3].sum(2)>0)).sum()),')')"
```

Les trois conditions doivent être réunies :

```text
alpha inchange            = True
RGB intra-masque inchange = True
RGB colore hors masque    = 0   (et > 0 avant)
```

Une seule fausse ⇒ ne pas installer.

Après installation, refaire le test 2 sur `iee-assets/areas/<ZONE>/` pour confirmer que les assets
posés sont bien les assets neutralisés.

## Variante intra-masque — fondu radial premultiplié

Si le carré, le halo ou le fond est **opaque**, il fait partie du sprite et existe en vanilla.
`--mode zero` ne le retirera pas : il ne nettoie que la zone déjà transparente.

Discriminant :

```powershell
python -c "import numpy as np,glob; from PIL import Image; c=[(np.asarray(Image.open(f).convert('L'))>0).mean() for f in sorted(glob.glob(r'<frames_x1>/alpha/*.png'))]; print('couverture alpha moyenne %.1f%%'%(100*np.mean(c)))"
```

Couverture élevée (> 85 %) avec un pourtour sombre opaque ⇒ défaut intra-masque.

Le correctif n'est alors pas d'effacer le carré mais de **le remplacer par un halo assumé** :
construire un fondu radial elliptique, centré sur l'ancre `centre_x1` propre à chaque frame, puis
le baker dans le RGB avec `premultiply`. C'est un choix esthétique, à faire valider en jeu.

```powershell
python pipeline/scripts/build_alpha_feather.py `
  --resref <RESREF> --run <run-x4> `
  --radial-outer-x-x4 <rx> --radial-outer-y-x4 <ry> --radial-inner-fraction <f> `
  --output proto/<RESREF>-radial-<variante>

python pipeline/scripts/build_blended_rgb_neutral_pack.py `
  --split-root <split-source> --output <split-neutralise> `
  --resref <RESREF> --mode premultiply `
  --feather-proto proto/<RESREF>-radial-<variante>
```

Dimensionner l'ellipse sur l'étendue réelle du cœur clair par rapport à l'ancre, pas sur le
cadre :

```powershell
python -c "import numpy as np,json; from PIL import Image; u=r'<run>/resources/<RESREF>/02_upscale_x4'; m=json.load(open(u+'/manifest.json')); f=[x for x in m['frames'] if x['frame']==<INDEX>][0]; lum=np.asarray(Image.open(u+'/rgb/frame_%03d.png'%<INDEX>).convert('RGB')).astype(float).mean(2); cx,cy=[v*4 for v in f['centre_x1']]; ys,xs=np.where(lum>120); print('dx',xs.min()-cx,xs.max()-cx,'| dy',ys.min()-cy,ys.max()-cy)"
```

Contrôler après coup que la luminance d'un coin tombe à 0 et que celle du cœur est inchangée.

Référence validée : `FLAME2S` — 12×12 px, couverture alpha 91,7 % en x4, carré olive opaque de
luminance moyenne 55. Trois correctifs alpha antérieurs sans effet avaient fait classer la
ressource `écarté` « carré natif au moteur ». Fondu radial `18×28 px x4`, `inner-fraction 0,45`,
puis `premultiply` : coin `27,8 → 0,0`, cœur `188,4 → 188,4`. QA validée sur AR0602 le 2026-08-27.

Une ressource `écarté` pour « défaut natif » après des corrections **alpha seules** est donc
toujours à réexaminer sous cet angle : la conclusion « natif au moteur » peut n'être qu'un
symptôme de l'inefficacité structurelle de ces corrections sur le chemin blended.

## Références validées

| Resref | Zone | Flags | Mode | Mesure avant → après | QA |
|---|---|---|---|---|---|
| `AM0900DM` | AR0900 | `0x1003` | `zero` | 422 574 texels transparents, **0** coloré | 2026-08-27 |
| `FIRE_1` | AR0700 + 7 zones | `0x1003`, `0x1043`, `0x1103`, `0x43` | `zero` | 5 344 → **0** (lum. max 196) | 2026-08-27 |
| `FIRE_4` | AR0700 + 77 zones | `0x1003` et variantes | `zero` | 2 257 → **0** (lum. max 187) | 2026-08-27 |
| `FLAME2S` | AR0602 | `0x1003` et variantes | `premultiply` + radial | coin `27,8 → 0,0`, cœur inchangé | 2026-08-27 |

Lot `FIRE_1` + `FIRE_4` : `--mode zero`, 1 212 frames et 2 880 282 pixels modifiés sur 83 zones,
alpha et RGB intra-masque inchangés, pack `combined-20260827-plus-ar0700-fire-rgb-neutral`.
`FLAME2S` : `--mode premultiply` avec fondu radial, 27 frames et 53 236 pixels, pack
`combined-20260827-plus-flame2s-ar0602-radialA` ; servi sur AR0602 seulement.

Ressources restant à évaluer dans cette classe : `FPIT1S` (installé, fuite mesurée à 100 %),
`FLAME2M`, `FIRE_4GS`, et les 76 zones de `FLAME2S` non encore servies.

## Conditions d'arrêt

- Un seul des deux tests d'entrée positif ⇒ ne pas appliquer.
- `frames_changed == 0` ⇒ diagnostic faux.
- Une vérification avant installation fausse ⇒ ne pas installer.
- Alpha dégradé avec `--mode zero` ⇒ interdit, employer `premultiply`.
- Défaut opaque intra-masque ⇒ hors périmètre.
- Ne jamais enchaîner une correction alpha sur une ressource `Blended` sans avoir d'abord
  neutralisé le RGB et refait une QA.
