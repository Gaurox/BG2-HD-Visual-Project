# Audit projectiles —2026-10-28

## Décision

- Sélection50 : **49/50 images déjà produites et installées** ; BGLRYU seul sans sortie. Pas de nouveau lot50 d'inférence justifié.
- 49graphismes de vol →181PRO stock : **181/181 références primaires actives présentes au catalogue HD**. Cela vérifie le raccord statique ; pas une acceptation visuelle de181projectiles complets.
- 34graphismes avec preuve d'asset accepté,15avec pack de palette vérifié. La QA des images ne valide pas tous les consommateurs PRO.
- BGLRYU : fumée potentielle BGLRY ; chemin moteur à confirmer avant production.

## Inventaire complet actualisé

| Unité | Résultat |
|---|---:|
| PRO stock |243|
| BAM visuels explicites +fumées/fragments INI |107|
| BAM avec sortie réutilisable |96|
| Masques noirs natifs, sans IA |8|
| BAM sans sortie |3|
| Contextes source+palette réutilisables |164/175|
| Dont asset accepté /pack de palette vérifié |80/84|
| Contextes masques /manquants |8/3|

- Manques image : BGLRYU,SPCL236U,SPGLYPHI. Ne lancer qu'après confirmation du rôle moteur.
- PRO avec BAM primaire déclaré :195 ; **189/195 au catalogue HD**, dont les181liés à la planche et8symboles d'école.
- 5PRO hors catalogue HD attendus : DRAGBLCK→SPSDRABU ; SPARBKNP/SPARBKPA/SPARKLBK/SPKLARBK→TRAVELB. Masques natifs ; absence HD ≠ panne.
- **LIGHTSTO→MAGMIS : dépendance absente de KEY/BIF/catalogue**. Usage réel et branche moteur à résoudre ; ne pas substituer SPMAGMIS par supposition.
- 48PRO sans BAM primaire déclaré : routes indirectes/procédurales ; absence d'un BAM primaire ≠ projectile manquant.

## Liaisons actives vérifiées

- Jeu lu via `config://bg2ee_game_root` ; manifest SHA256 `33EABE45E817E000E33BA9A96DD0B758E356FC1DAEC79BBF548774E669C60316`.
- 522ressources/59699backings au catalogue ; SHA registre conforme au manifeste.
- Lot31 : **134/134PRO** correspondent exactement au stock +référence BAM attendue ; palette_job et encodage conformes au routage. Aucun autre octet PRO changé dans ce périmètre.113références reroutées,21noms natifs adéquats.
- Autres routes primaires HD :55PRO ; assets acceptés. Dont8symboles d'école exclus de la planche.
- INSEC1..4 :4PRO complets conformes au stock +8patchs documentés du27octobre. Les modifications secondaires INSEC2/3 sont attendues (`0x21c`,`0x230`), pas des anomalies.3alias droits vérifiés,384backings SHA conformes.
- 11915backings/4219468096octets : SHA256 vérifiés,0manquant/altéré.132carriers BAM : SHA256 vérifiés,0écart. Périmètre : noms de la sélection +cibles primaires HD des243PRO ; complément insectes ci-dessus. Pas de rehash global des59699backings.
- Cycle primaire déclaré trouvé pour189/189PRO liés au catalogue.
- Probe natif : **133160contrats passent**, catalogue prêt ; dimensions/slots/phases vérifiés hors jeu, aucun draw observé par cette sonde.
- INI actif : `EnableEffectAnimationX4=true`, `EnableEffectAnimationStreaming=true`, `EffectMetadataMiB=32`.
- Journal dernière session `2026-10-27 23:40:11..14` :522ressources/59699frames chargées ; scopes `CProjectileBAM::Render`, `CVEFVidCell::Render`, `CInfinity::FXRender` installés. Preuve historique d'activation moteur ; aucune extrapolation vers tous les draws.

## Ce qui reste à établir

- Le raccord primaire est présent. L'apparence complète exige encore les essais ingame du lot31 : palettes, orientations, ancrage, alpha/mélange, cadence et comportement du propriétaire. Le reçu d'installation ne vaut pas QA.
- MAGICMIS possède une preuve historique ingame ciblée ; les nuées ont une acceptation du27octobre. Préserver ces portées ; pas de validation universelle des243PRO.
- 29routes fumée,4fragments,21explosions moteur +particules : une entrée au catalogue du BAM primaire ne prouve pas leur substitution HD.
- `work-items.csv` conserve243QA `not-assessed` au niveau PRO ; ce champ ne retire pas les QA d'assets/historiques acquises.
- Priorité utile : essais des projectiles déjà raccordés ; résolution LIGHTSTO ; identification des3sources manquantes et des routes moteur. Pas de nouvelle inférence des49images existantes.

## Preuves

- `analysis.json`, `contexts.json`, `visual-assets.csv` : actualisation des sources/productions/QA.
- `live-audit.json`, `live-pro-routes.csv`, `audit_live.py` : catalogue,134routages, cycles, carriers etSHA des textures.
- `live-insects-supplement.json` :4PRO complets/8références et encodage droit.
- `live-contracts.tsv`, `live-catalogue-probe-current.log` :133160contrats courants. Contrats hérités du reçu27octobre ; ne pas réutiliser seuls ceux du19octobre pour SPINSECT.
- `live-catalogue-probe.log` : premier appel avec mauvais répertoire ; échec de chemin uniquement. `live-catalogue-probe-correct-path.log` : ancien contrat SPINSECT obsolète ; remplacé pour le contrôle final, aucun fichier installé modifié.
- L'audit écrit seulement l'instantané et ses projections projectiles ; pas d'inférence, installation, QA ou release accordée.
