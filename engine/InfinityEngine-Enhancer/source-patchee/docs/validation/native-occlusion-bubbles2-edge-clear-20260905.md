# Occlusion native — expansion xN de BUBBLES2

Statut : correction validée ingame par l'utilisateur le 2026-09-05 sur les 28 occurrences de
`BUBBLES2` : AR0411 (6), AR0602 (12), AR0603 (10).

## Cause et correction

- `BUBBLES2` est `Blended`; un RGB non nul reste visible même avec alpha nul.
- xBR2 blend étend certains pixels dans une cellule logique transparente du BAM x1.
- Le transfert d'occlusion natif ne modifiait pas cette cellule vide : le contour xN survivait
  hors décor sous forme de points.
- Le canal B du transfert marque uniquement une cellule x1 transparente située à une distance de
  Chebyshev 1 d'un effacement natif complet.
- Le shader écrit alors RGBA `(0,0,0,0)`. Les pixels natifs, les visibilités partielles et les
  cellules lissées non voisines d'une occlusion restent inchangés.

Mesure d'entrée : 8 906 cellules logiques étendues sur 214 frames; distance maximale 1 par rapport
au support alpha x1.

## Identités et QA

| Élément | Identité |
|---|---|
| DLL Debug validée | `14AC6AFDD87A5976F6167FF6FE2B60E4CE94C9806B96473D81EDCCCE5DB2E404` |
| INI | `5F76B2F04779D2A06838A0A11A2031FC393064FAF6EAC27CB434B1212C381C53` |
| Transaction renderer | `backups/renderer/20260904T235715569754Z-8ebed3c8/renderer-install-receipt.json` |
| Pack QA canonique | `animations/packs-par-zone/bubbles2-xbr2x-blend-3areas-premultiply-budget-20260905` |
| Manifeste du pack | `A3B04D2EF8B5C949340E42868B734291FD1EC86EBC31E41FCC14766976E9DA05` |
| Log final | `E527C9F636835A92BD1DFD0137BF2003E8C19C8095F8EF5E5B2190455E0FE3F4`, 0 ligne erreur |

Verdict utilisateur : bulles et occlusion correctes dans les trois zones; aucun résidu visible
hors décor. Les 1 437 textures/registres du pack canonique ont été comparés au jeu installé :
0 fichier absent, 0 divergence. La QA animation est enregistrée sous
`animations/index/qa-decisions/BUBBLES2/`.

## Régression intermédiaire écartée

La candidate `occlusion-bubbles2-edge-clear-20260905-v1` déclarait le transfert GLSL en `vec2`
tout en lisant `.b`. La compilation shader échouait (`C1031`) et le bridge restait inactif; les
bulles complètes apparaissaient hors décor. Capture `20260905015455_1.jpg`, SHA-256
`7BFC743ADB395306FAE77749A3BE5B58AB492660B6F10D4D048BD57CA142939A`.

La candidate v2 corrige la déclaration en `vec4`. L'instrumentation temporaire utilisée pour le
diagnostic a été retirée de la source de release; le comportement de rendu corrigé est inchangé.
Le binaire Release nettoyé et les suites automatisées restent à produire après choix explicite des
tests. Cette validation ne qualifie donc pas encore un nouveau `renderer-bundle.json`.
