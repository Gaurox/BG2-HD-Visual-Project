# WeiDU - développement, installation et compatibilité des mods

> **Statut :** Outil communautaire de référence  
> **Dernière vérification :** 2026-08-27

## Rôle

WeiDU est conçu pour développer, distribuer et installer des modifications pour les jeux Infinity Engine. Il sait lire et patcher de nombreuses ressources et vise la compatibilité entre mods.

## Pourquoi il est préférable à un simple dossier override

- applique des changements ciblés ;
- conserve un journal d’installation ;
- peut désinstaller un composant ;
- permet de détecter des ressources ou versions ;
- évite de remplacer des tables complètes ;
- gère les textes et traductions ;
- peut assembler une distribution reproductible.

## Principes pour un gros patch graphique

- séparer détection, installation et validation ;
- ne pas copier un fichier si le hash de base est inattendu sans avertissement ;
- générer ou installer les ressources par lots identifiables ;
- écrire un manifeste des fichiers ajoutés ;
- prévoir un mode vérification sans modification ;
- conserver les ressources lourdes hors du cœur logique si cela simplifie les mises à jour.

## UI et Lua

WeiDU peut installer les fichiers `M_*.lua` et ressources associées. Pour `UI.menu`, employer un patch contextuel très contrôlé ou un composant explicitement incompatible avec d’autres interfaces.

## Version de WeiDU

Utiliser une version stable récente compatible avec la plateforme et tester la distribution finale. Les versions et builds peuvent différer sur la prise en charge Unicode et l’architecture ; ne pas choisir automatiquement un binaire ancien parce qu’il est largement répandu.

## Sources
- Dépôt WeiDU: https://github.com/WeiDUorg/weidu
- Documentation WeiDU: https://weidu.org/WeiDU/README-WeiDU.html
