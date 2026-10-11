# Corbeille locale du projet

- Lot `animations-20261011-v1/` : 29 runs non retenus mais ambigus, déplacés avec leurs 22 réservations anciennes. Contenu conservé octet pour octet ; aucune validation déduite.
- Arborescence d'origine reproduite sous le lot : `animations/runs/`, `animations/batches/`, `animations/ressources/<REF>/runs/`.
- `animations-20261011-v1/manifest.json` : chemins d'origine/destination, SHA de chaque fichier, raisons de quarantaine et liens vers l'audit/reçu.
- Payloads locaux ignorés par Git ; manifest et documentation versionnés. Le déplacement ne libère pas d'espace disque.
- Récupération : choisir l'entrée du manifest ; vérifier ses SHA ; déplacer `destination` vers `source` sous la racine du dépôt, seulement si l'ancien chemin est libre. Pour un run réservé, restaurer aussi sa réservation associée. Ne pas modifier les manifests historiques contenus dans les dossiers.
- Ne pas vider ce dossier avant décision explicite sur les cas conservés.
