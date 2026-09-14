# Runtime de développement

Le runtime est installé indépendamment des assets. Le manifeste choisi fixe la DLL et ses
capacités ; un installateur de sprite vérifie uniquement que cette DLL est déjà live.

Installer une DLL seulement si le manifeste requis diffère de la DLL active. Pour les catalogues
xBR et ReboutCX, utiliser les commandes de [`../../sprite/FAMILY_APPEND.md`](../../sprite/FAMILY_APPEND.md).

Contrat :

- le runtime ne copie que `InfinityEngine-Enhancer.dll` et possède son propre rollback ;
- l'installation d'assets ne modifie jamais la DLL ;
- le catalogue et l'INI sont sauvegardés puis remplacés atomiquement ;
- tout shard source/référencé est hashé avant activation ; un shard conforme déjà présent n'est pas recopié ;
- les nouveaux shards restent inertes après restauration ; seul le catalogue les active ;
- l'installateur vérifie l'état physique actif ; `verify --full-verify` reste l'audit de production réservé à la finalisation.
