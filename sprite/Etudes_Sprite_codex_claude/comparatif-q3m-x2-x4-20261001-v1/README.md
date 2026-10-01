# Comparatif ingame Q3m x2 / x4 — 2026-10-01

- Ouvrir [comparatif.html](comparatif.html) par double-clic dans Chrome/Edge ; autonome, fonctionne hors ligne, sans serveur ni fichiers vidéo externes.
- Curseur : x2 à gauche, x4 à droite ; boutons `Tout x2` / `Tout x4`, lecture commune en boucle, ralenti ×0,5/×0,25, pas image, zoom personnage ×3, plein écran.
- Sources : captures utilisateur `x2.mp4` / `x4.mp4`, 2560 × 1440, 60000/1001 images/s. MP4 originaux intégrés en base64 ; aucun réencodage supplémentaire. Le HTML conserve la compression déjà présente dans les captures.
- Provenance : [sources.json](sources.json), tailles/SHA-256 des deux MP4 et du HTML. Taille HTML : 14 037 475 octets.
- Synchronisation initiale : `t_x4 = t_x2 + 10 × 1001/60000`, soit +0,166833333 s ; alignement sur le guerrier sélectionné. Les autres acteurs peuvent avoir des phases différentes. Décalage ajustable dans la page.
- Portion commune : environ 5,39 s ; animation d'attente. Le zoom ×3 agrandit la capture, sans créer de détail.
- Observation visuelle : cadence et poses comparables ; x2 plus compact/contrasté, x4 plus doux sur les contours et les transitions de l'armure. Préférence légère pour x4 en mouvement, sans décision QA définitive.
- Limites : cet extrait ne valide pas marche, attaques, toutes les directions, palettes/effets, changements d'équipement, continuité à froid, reset graphique ou FPS/p95. Aucun statut `accepted` ni release déduit.
- Suite utile : compléter P3 ingame, comparer échelle/filtrage P4 au zoom joué, puis étendre via la déduplication. Q8c/frontières reste un essai distinct avant toute adoption.
- Maintenance : [comparatif.template.html](comparatif.template.html) contient `__X2_DATA_URL__` / `__X4_DATA_URL__` ; le livrable ouvrable est `comparatif.html`. L'artefact final est conservé octet pour octet depuis le comparatif initial.
- Packs expérimentaux : [x2](../../catalogs/palette-q3m-human-fighters-x2-20261001-v1/README.md), [x4](../../catalogs/palette-q3m-human-fighters-x4-20261001-v1/README.md) ; 0x6100/0x6110 uniquement, Garlena 0x6010 conservée native.
