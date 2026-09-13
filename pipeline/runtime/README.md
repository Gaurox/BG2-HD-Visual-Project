# Runtime de développement

Le runtime est installé indépendamment des assets. Le manifeste choisi fixe la DLL et ses
capacités ; un installateur de sprite vérifie uniquement que cette DLL est déjà live.

```powershell
pwsh pipeline/scripts/Install-IEE-Runtime-Test.ps1 -Mode Install -Manifest pipeline/runtime/manifests/iee-water-ar1000n-creature-catalog-v2-v1.json
python pipeline/scripts/run_creature_sprite_x2.py install --job <catalog-job>
python pipeline/scripts/run_creature_sprite_x2.py restore --job <catalog-job>
pwsh pipeline/scripts/Install-IEE-Runtime-Test.ps1 -Mode Restore
```

Contrat :

- le runtime ne copie que `InfinityEngine-Enhancer.dll` et possède son propre rollback ;
- l'installation d'assets ne modifie jamais la DLL ;
- le catalogue et l'INI sont sauvegardés puis remplacés atomiquement ;
- un shard au nom content-addressé déjà présent est réutilisé sans lecture ni hash ;
- les nouveaux shards restent inertes après restauration ; seul le catalogue les active ;
- les vérifications physiques exhaustives sont réservées à la finalisation.
