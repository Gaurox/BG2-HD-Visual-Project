# Actions ajoutées et documentées en version 2.0

> **Statut :** Officiel Beamdog - paraphrase technique  
> **Dernière vérification :** 2026-08-27

## Liste documentée

| Action | IDS | Effet |
|---|---:|---|
| `SetGlobalTimerRandom(S:Name*, S:Area*, I:Min*GTimes, I:Max*GTimes)` | `377` | Définit un délai aléatoire entre un minimum et un maximum. |
| `ResetPlayerAI()` | `409` | Restaure pour le PNJ courant le script indiqué dans `PARTYAI.2da`. |
| `MoveToObjectOffset(O:Target*, P:Offset*)` | `386` | Déplace la créature vers les coordonnées de la cible avec un décalage X/Y. |
| `ZoomLock(I:Lock*BOOLEAN)` | `412` | Réinitialise le zoom puis le verrouille si vrai ; le déverrouille si faux. |
| `RandomWalkTime(I:Time*)` | `410` | Marche aléatoire jusqu’à un nombre documenté de changements de direction. |
| `RandomWalkContinuousTime(I:Time*)` | `411` | Variante continue ; la description du PDF est pratiquement identique à la précédente. |
| `DisplayStringHeadNoLog(O:Object*, I:StrRef*)` | `388` | Affiche un texte au-dessus d’un objet sans l’écrire dans le journal de combat. |
| `DisplayStringPointLog(I:Strref*, P:Location*)` | `408` | Affiche un texte à des coordonnées et l’écrit dans le journal de combat. |

## Points d’attention

### Minuterie aléatoire

Le minimum et le maximum sont des valeurs `GTIMES`. Tester les bornes et le comportement lorsque les valeurs sont identiques ou inversées. Employer un nom de variable propre au mod pour éviter les collisions.

### Marche aléatoire

La documentation 2.0 donne une description très proche pour les deux actions. La différence réelle doit être vérifiée dans l’IESDP ou expérimentalement. Ne pas déduire le comportement uniquement du nom.

### Déplacement avec offset

Valider : collision, zone inaccessible, cible mobile, transition de zone, interruption par combat et position finale. Un offset mathématiquement correct peut rester invalide sur la search map.

### Affichage de texte

Les actions sont utiles pour instrumenter un scénario de test sans polluer ou, au contraire, en conservant une trace dans le journal.

## Convention de scripts de test

Créer un composant de debug désactivé par défaut qui :

- utilise des StrRef dédiées ;
- préfixe les variables globales ;
- n’altère pas les scripts originaux de façon irréversible ;
- peut être désinstallé proprement par WeiDU.

## Sources
- Release notes officielles 2.0: https://files.beamdog.com/files/BG-2.0-ReleaseNotes.pdf
