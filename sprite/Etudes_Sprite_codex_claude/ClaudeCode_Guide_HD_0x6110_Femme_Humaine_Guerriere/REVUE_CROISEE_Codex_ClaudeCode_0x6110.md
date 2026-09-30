<!-- Transcription documentaire du HTML Claude du 2026-09-29 ; aucune nouvelle mesure. -->
<!-- Source SHA-256 : d72246da51c2e7b2c5f76006b817ead9d2b5cdda5499933c20bfb2b8a69c046e -->
<!-- Table interactive matérialisée depuis donnees_v3/e5_table.json, comparée au JSON embarqué. -->

> Archive de la revue du 2026-09-29, transcrite le 2026-09-30. Les conclusions et métriques historiques restent celles de son auteur ; consulter le guide définitif et P1 pour les corrections ultérieures. Les visuels restent locaux.

Revue croisée · Claude Code lit Codex

# Revue croisée Codex 0x6110

Lecture complète du dossier Codex, vérification de ses affirmations, test de mes méthodes sur son corpus et ses palettes, puis verdict : ce qu'il a trouvé que je n'avais pas, ce que mon travail lui apporte, et la méthode fusionnée que je recommande.

**Claude Code** (Claude Opus 5.5) 29 septembre 2026 Dossier lu : `CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29` (1 560 fichiers, 41 Mo)

Dossier Codex lu sans modification Validation croisée E5 exécutée Dépôt intact Aucun essai en jeu

## Verdict

Convergence

Sans se lire, Codex et moi aboutissons à la même architecture : garder les 7 gammes de 12 nuances comme contrat de couleur, et faire mélanger deux nuances voisines par le DLL du projet, après le calcul de la palette réelle de chaque calque. Deux recherches indépendantes qui convergent, c'est le signal le plus fort de ce dossier.

Codex meilleur

Sur l'enquête moteur et l'inventaire, Codex est plus rigoureux que moi. Il a désassemblé l'exécutable lui-même, a montré que le jeu lit `MPALETTE.BMP` et non `RANGES12.BMP`, a trouvé le bon préfixe des poupées d'inventaire (`WPN`) et a trié ce qui est réellement équipable. Il propose aussi deux pistes que je n'avais pas.

Claude meilleur

Sur la méthode de palettisation elle-même, ma proposition va plus loin. Codex décrit l'ajustement sur plusieurs palettes et le traitement des frontières sans les implémenter. Je les ai implémentés et mesurés. Sur son propre corpus et ses propres palettes, ma méthode Q8 fait 20 % d'écart en moins que son interpolation sur les palettes jamais vues.

Recommandation

La proposition de Codex n'est pas meilleure que la mienne ; c'est un sous-ensemble de ma méthode pour le cœur du sujet. Son travail améliore pourtant le mien sur six points précis. La bonne suite est une méthode fusionnée : ma palettisation, ses fondations moteur, son inventaire et son protocole de test.

## Bilan par domaine

| Domaine | Codex | Claude Code | Avantage |
| --- | --- | --- | --- |
| Preuve moteur | Désassemblage indépendant (capstone), xrefs `MPALETTE` → `SetRange` | Repris de l'audit P6.1 du dépôt | Codex |
| Fichier de gammes réellement lu | `MPALETTE.BMP` | `RANGES12.BMP` (pixels identiques, mauvais fichier à modifier) | Codex |
| Inventaire | 774 BAM de stock, 536 équipements utilisables, 81 poupées `WPN`, mains gauche séparées, noms des séquences | 656 BAM depuis l'index du projet, `H6` et `ZW` gardés à tort, poupées mal préfixées | Codex |
| Couleurs fixes supplémentaires | Canal d'équipement inutilisé fixé par l'objet, lignes ancres blanche 74 et noire 75 | « Aucune » (vrai pour le corps, faux pour les équipements) | Codex |
| Palettisation dans la gamme | Interpolation continue, réglée sur une seule palette | Sous-nuance 3 bits réglée sur 3 palettes | Claude |
| Frontières entre gammes | Idée décrite, non testée | Mélange pondéré à 1/8 implémenté et mesuré | Claude |
| Précision nécessaire | 2 indices + poids 8 bits (3 octets par pixel) | 3 bits suffisent, mesuré (taille ×2 à ×2,3) | Claude |
| x2 contre x4 à l'écran | Coût mémoire seulement | Analyse de la réduction à l'affichage selon le zoom | Claude |
| Tramage | Bayer testé, blur σ 0,5 : léger gain après moyennage ; option locale | Bayer et diffusion testés, crénelage à l'écran, rejetés | Accord |
| Scintillement | Correspondances conservatrices, sans suivi de mouvement | Pixels immobiles alignés, erratum sur mon premier échantillon | Les deux incomplets |
| Protocole de test en jeu | Mire 256 indices, deux personnages même BAM, test MPALETTE seul, identité i=j | Plan par blocs, commandes console et EEex | Codex sur la conception |
| Documents | Guide HTML + notes détaillées, inventaire CSV | Guide, présentation interactive avec comparateur | Complémentaires |

## Ce que nous avons trouvé tous les deux

- La limite des 12 nuances vient du moteur false-color, pas du BAM. Indices : 0 transparent, 1 ombre, 2-3 noirs réservés, 4-87 sept gammes, 88-255 vingt et un mélanges de paires.
- Formule des mélanges : moyenne entière RGB des nuances 2 à 9 de deux gammes. Near Infinity et GemRB ne sont pas des oracles fiables pour ce point.
- Le pipeline actuel limite les candidats aux indices de la frame d'origine ; lever cette limite ne rapporte que 3 à 6 %.
- ReboutCX dépend de la palette d'entrée : le même sprite ré-inféré sous d'autres couleurs change 20 à 44 % de ses indices (mesure Codex), avec un plancher d'erreur d'environ 0,04 sur les palettes jamais vues (ma mesure). Il faut régler la recette sur plusieurs palettes.
- Pas de tramage par défaut. Un bruit renouvelé à chaque image est exclu.
- La voie à fort gain est une interpolation entre nuances voisines, faite dans le DLL IEE existant après capture de la palette réelle. Ne pas créer un second hook via EEex.
- ReboutCX x4 comme source de travail ; x2 comme candidat de livraison.

Ce que Codex a trouvé et que je n'avais pas

## Apports de Codex

| Apport | Ma vérification | Effet sur mon travail |
| --- | --- | --- |
| **Le moteur lit `MPALETTE.BMP`**, pas `RANGES12.BMP`. | Vérifié La chaîne « MPALETTE » est présente une fois dans `BaldurReal.exe` ; « RANGES12 » est absente. | Mes mesures restent justes (pixels identiques), mais toute modification de gamme doit viser `MPALETTE`. |
| **Poupées d'inventaire en `WPN`** (81 BAM `INV`/`OIN`). | Vérifié 81 ressources `WPN*` dans la clé du jeu. | Mon guide écrivait `WPM` : erreur corrigée. |
| **Périmètre utile** : 92 corps + 536 équipements portables par une humaine guerrière. `H6` = attaques de créatures (59 objets), `ZW` interdit aux humains, `D0` sans objet. | Non recalculé Cohérent avec l'index du projet. | Retirer `H6` et `ZW` de ma liste de production. |
| **Canal d'équipement fixé par l'objet** : une arme qui n'utilise pas la peau ou les cheveux peut recevoir, via l'opcode 7 de son ITM, une gamme constante sur ce canal. | Vérifié Les lignes 74 (blanc), 75 (noir), 76-78 (rouge, vert, bleu purs) sont constantes. | Bonne réponse à « quelles couleurs fixes exploiter ». Coût : patcher les ITM de tous les objets du même code, risque de conflit avec d'autres mods. |
| **Gammes propres par acteur** dans le DLL, sans toucher la table globale ; méthode de conception L(t), C(t), h(t) par matière. | Accepté comme option | Utile seulement si des bandes restent après l'interpolation. |
| **Contrat de dépendances palette** : ne pas remplir de faux « représentants » pour faire accepter des indices absents de la frame d'origine. | Accepté Le DLL ne vérifie que la présence, mais le sens du champ change. | Ma phase A doit passer par une version de registre qui déclare explicitement ses dépendances palette. |
| **Noms des séquences du corps** : G11 marche, G1 garde une main, G12 repos, G13 garde deux mains, G14 touchée, G15 mort, G16 au sol, G17-18 repos, G19 sommeil et relevé, CA 4 sorts, A7/A9 deux armes. | Cohérent avec mes découpes de cycles. | À reprendre dans le plan de tests. |
| **Tests en jeu** : mire des 256 indices, deux personnages même BAM avec palettes opposées, modification de `MPALETTE` seule, rendu identité i=j avant i≠j. | Accepté | Ajouté au plan fusionné. |
| **Tramage après moyennage** : avec un flou σ 0,5, le Bayer réduit l'erreur (0,0139 → 0,0125) alors qu'il l'augmente pixel par pixel. | Compatible avec mon analyse d'affichage. | Le Bayer n'aide que si l'affichage moyenne les texels ; en plus proche voisin réduit, il crénelle. L'interpolation fait mieux dans les deux cas (0,0114). |

Expérience E5

## Validation croisée sur le corpus de Codex

Pour trancher, j'ai rejoué mes méthodes sur les données de Codex plutôt que sur les miennes : cycle d'attaque complet (14 images) du corps `CHFB1A1`, de l'épée `WQNS0A1`, du bouclier `WQNC0A1` et du casque `WQNJ6A1`. Les palettes de test sont ses profils « contrast » et « pale », plus ma palette D ; aucune n'a servi à régler une méthode. Sa méthode est exécutée avec sa propre fonction `quantize_modes`, importée en lecture seule depuis son dossier.

| Échelle | Méthode | REF | D | CX-contrast | CX-pale | Inédites | Scint. REF | Scint. CX-contrast | Scint. CX-pale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| x2 | xBR | 46.5 | 53.3 | 46.1 | 42.6 | 47.3 | 5.23 | 6.07 | 10.17 |
| x2 | Q0_actuel | 33.4 | 55.7 | 42.5 | 44.4 | 47.5 | 3.77 | 5.26 | 11.18 |
| x2 | Q1_classe | 32.3 | 56.7 | 42.9 | 45.2 | 48.3 | 3.68 | 5.71 | 11.4 |
| x2 | Q6_idx_multi | 39.1 | 49.0 | 41.0 | 40.2 | 43.4 | 5.14 | 5.89 | 11.98 |
| x2 | Q3_frac_ref | 25.7 | 54.2 | 38.4 | 42.6 | 45.1 | 0.6 | 4.55 | 13.44 |
| x2 | CX_interp_ref_lin | 26.7 | 53.7 | 38.1 | 42.6 | 44.8 | 0.6 | 5.08 | 13.94 |
| x2 | CX_codex_exact | 26.4 | 53.9 | 38.1 | 42.7 | 44.9 | 0.6 | 4.82 | 13.58 |
| x2 | CX_codex_bayer | 35.9 | 58.7 | 45.6 | 47.6 | 50.6 | 3.86 | 6.6 | 12.49 |
| x2 | Q8_srgb | 28.6 | 41.1 | 31.9 | 33.7 | 35.6 | 3.0 | 5.17 | 13.07 |
| x2 | Q8x_srgb_exact | 28.7 | 41.2 | 32.0 | 33.9 | 35.7 | 3.26 | 5.44 | 13.22 |
| x2 | Q8x_lin_exact | 28.9 | 41.8 | 32.2 | 34.0 | 36.0 | 3.26 | 5.08 | 14.16 |
| x4 | xBR | 47.7 | 55.0 | 47.1 | 43.5 | 48.6 | 5.15 | 5.77 | 9.52 |
| x4 | Q0_actuel | 34.0 | 58.1 | 44.2 | 45.8 | 49.4 | 3.3 | 5.27 | 11.66 |
| x4 | Q1_classe | 32.8 | 59.2 | 44.8 | 46.9 | 50.3 | 3.21 | 5.5 | 12.12 |
| x4 | Q6_idx_multi | 40.3 | 51.3 | 42.5 | 41.6 | 45.1 | 4.76 | 5.5 | 11.91 |
| x4 | Q3_frac_ref | 26.3 | 56.8 | 40.5 | 44.4 | 47.2 | 1.02 | 4.93 | 13.96 |
| x4 | CX_interp_ref_lin | 27.4 | 56.3 | 40.1 | 44.2 | 46.9 | 1.04 | 5.15 | 14.87 |
| x4 | CX_codex_exact | 27.1 | 56.5 | 40.1 | 44.4 | 47.0 | 1.02 | 4.97 | 14.66 |
| x4 | CX_codex_bayer | 36.3 | 61.1 | 47.3 | 49.1 | 52.5 | 3.25 | 5.36 | 12.93 |
| x4 | Q8_srgb | 30.7 | 43.6 | 34.3 | 35.6 | 37.8 | 3.27 | 4.93 | 12.59 |
| x4 | Q8x_srgb_exact | 30.7 | 43.7 | 34.4 | 35.7 | 37.9 | 3.52 | 5.06 | 12.81 |
| x4 | Q8x_lin_exact | 30.8 | 43.9 | 34.5 | 35.8 | 38.1 | 3.43 | 5.11 | 13.11 |

Écart = ΔE OKLab moyen ×1000 par rapport à la sortie du modèle recalculée sous la même palette. « Inédites » = moyenne des palettes D, CX-contrast et CX-pale.

Palette

Corps `CHFB1A1`, image 6, x4. De gauche à droite : Q0 actuel, Q6 multi-palettes, interpolation Codex, Q8 Claude, Q8 en lumière linéaire, sortie du modèle.

### Lecture

- La méthode de Codex et ma variante Q3 sont en fait la même idée : une interpolation dans la gamme réglée sous une seule palette. Elles obtiennent les mêmes chiffres (47,0 et 47,2 en x4). Elles sont excellentes sous la palette de réglage (27 contre 34 pour Q0) et ne gagnent que 5 % sur les palettes jamais vues.
- Q8 (réglage sur 3 palettes + mélange aux frontières) gagne 23 % sur les palettes jamais vues par rapport au pipeline actuel, et 20 % par rapport à Codex. Sur ses deux profils seulement : −14 % (contrast) et −20 % (pale).
- Sous le profil « pale », la méthode de Codex laisse des liserés gris et noirs autour des protège-bras et du buste ; on les voit aussi dans sa propre figure `runtime_interpolation_recolor.png`. Q8 les supprime presque tous.
- Lumière linéaire ou octets sRGB pour l'interpolation : aucune différence mesurable (38,1 contre 37,8). Le choix de Codex est correct mais pas nécessaire.
- Le scintillement n'est pas tranché sur ce cycle d'attaque. Peu de pixels restent immobiles (4 521 en x4) et, sous le profil « pale », les méthodes scintillent entre 10 et 15 %. Codex avait raison : il faut une mesure qui suive le mouvement des membres.

Figure de Codex, copiée sans modification. Interpolation réglée sur une palette, rendue sous trois palettes. Les liserés aux frontières de gammes restent visibles sous « contrast » et « pale ».

Figure de Codex, copiée sans modification. Gammes vanilla et redistribution à écarts égaux. Un diagnostic de régularité, pas une recommandation artistique : je partage cette réserve.

Ce que mon travail apporte au sien

## Apports de mon travail

| Point | Chez Codex | Chez moi |
| --- | --- | --- |
| Réglage sur plusieurs palettes | Formule J(i) proposée, « reste à implémenter » | Implémenté (Q6 en indices, Q3m/Q8 en sous-nuances), validé sur ses palettes |
| Frontières entre gammes | « Reconstruire la couverture des deux matériaux », non testé | Mélange de deux gammes à poids 1/8, erreur des pixels frontière −16 à −48 % |
| Format runtime | i, j, poids 8 bits : 3 octets par pixel | Indice + 3 bits vers la nuance suivante (+ plan frontière) ; 2 et 4 bits mesurés |
| Solution installable tout de suite | Aucune, sinon xBR ou l'actuel | Q6 : −9 % d'écart sur ses palettes inédites, sans modifier le rendu du DLL |
| x2 ou x4 | Question de mémoire | Question de zoom : x4 réduit à l'affichage crénelle en plus proche voisin, filtrage nécessaire |
| Présentation | Planches fixes | Comparateur interactif, explorateur de palette recalculée |

## Désaccords

### xBR comme livraison prudente

Codex garde xBR x2/x4 comme « candidat de livraison conservateur ». ReboutCX est déjà installé et accepté en jeu sur le guerrier humain `0x6100`, et Q6 comme Q8 font mieux que xBR sur toutes les palettes testées. xBR reste la base de repli, pas la cible.

### Tramage local en option

Codex garde un Bayer faible et localisé comme option contre les bandes. Une fois l'interpolation disponible, les bandes disparaissent sans motif ; je retirerais cette option du plan.

### Priorité des gammes redessinées

Redessiner les 12 nuances par matière change les couleurs que le joueur a choisies. L'interpolation comble déjà les grands écarts entre nuances. Je la placerais après la validation en jeu de V6, seulement si des bandes persistent.

### Canal fixé par l'objet

Bonne idée, mais elle exige de patcher des ITM partagés par beaucoup d'objets et d'autres mods. Avec V6, un mélange vers le noir réservé (indice 2) donne des ombres fixes sans toucher aux ITM. À réserver à des objets précis.

Erratum 2

## Corrections de mon guide

| Guide v1 écrivait | Correction | Source |
| --- | --- | --- |
| `RANGES12.BMP` est la table des gammes | Le moteur lit `MPALETTE.BMP` ; `RANGES12` est une copie identique utilisée par Near Infinity | Codex, vérifié |
| Poupées d'équipement `WPM**INV` | `WPNxxINV` et `WPNxxOIN` (81 BAM) | Codex, vérifié |
| `H6` et `ZW` à produire | Hors périmètre : attaques de créatures et ailes interdites aux humains | Codex |
| Aucune couleur fixe supplémentaire exploitable | Vrai pour le corps ; pour les équipements, un canal inutilisé peut être fixé par l'objet (lignes constantes 74-78) | Codex, vérifié |
| Phase A sans toucher au DLL, via les représentants | Déclarer les dépendances palette dans une nouvelle version de registre ; le code de rendu du DLL ne change pas, sa lecture si | Codex |
| Q8 réduit le scintillement | Confirmé au repos ; non confirmé sur le cycle d'attaque de Codex | E5 |

Ce que je recommande maintenant

## Méthode fusionnée

| Étape | Contenu | Vient de |
| --- | --- | --- |
| 0 | Mesures en jeu rapides : zoom minimal et maximal, mire des 256 indices, modification de `MPALETTE` seule | Claude (zoom) · Codex (mire, MPALETTE) |
| 1 | Registre versionné avec dépendances palette explicites, puis quantifieur Q6 sur `CHFF4` + casque, bouclier, épée ; QA | Codex (contrat) · Claude (Q6) |
| 2 | Format V6 : indice + 3 bits + plan frontière ; test identité i=j ; test deux personnages même BAM | Claude (format, Q8) · Codex (tests) |
| 3 | Production sur 3 à 4 palettes, limitée aux 92 corps et 536 équipements réellement portables | Claude (réglage) · Codex (périmètre) |
| 4 | Filtrage de réduction pour x4 ; x2 livré par défaut tant que le zoom ne justifie pas mieux | Claude |
| 5 | Mesure de scintillement avec suivi du mouvement des membres | Codex (exigence) · Claude (mesure existante à étendre) |
| 6 | Options si besoin : canal fixé par l'objet pour quelques équipements, gammes propres par acteur | Codex |
| 7 | Poupées d'inventaire `CHFF1-4INV` et `WPN*` dans un lot séparé | Codex |

**Un seul x2 et un seul x4 à installer ?** Ma réponse ne change pas, et la validation croisée la renforce : Q6 en x2 et en x4 aujourd'hui, avec le contrat de dépendances de Codex ; Q8 dès que le DLL lit le format V6. Sur les palettes de Codex, Q6 gagne 9 % sur l'actuel et Q8 23 %.

## Fichiers

```text
ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/
REVUE_CROISEE_Codex_ClaudeCode_0x6110.html        ce document (nouveau)
figures_v3/cross_body6_*.png                      nouveau : validation croisée E5
figures_v3/codex_*.png                            copies des figures Codex citées
donnees_v3/e5_results.json, e5_table.json         nouveau : mesures E5
outils/e5_cross.py                                nouveau : script E5 (utilise e3b + quantize_modes de Codex)
(tous les fichiers précédents sont inchangés ; le dossier Codex n'a pas été modifié)
```

Revue produite par Claude Code (Claude Opus 5.5) le 29 septembre 2026. Les figures marquées Codex sont des copies de son dossier, sans modification. Les chiffres E5 viennent d'un seul cycle d'attaque, face sud, 4 calques ; ils ne valent pas validation en jeu.
