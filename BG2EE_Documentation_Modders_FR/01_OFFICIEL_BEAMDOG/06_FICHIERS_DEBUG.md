# Fichiers de debug officiels de l’Infinity Engine

> **Statut :** Officiel Beamdog, avec interprétation pratique  
> **Dernière vérification :** 2026-08-27

## Fichiers publiés

Beamdog met à disposition :

- les fichiers de debug Win64 pour la version **2.6.6.0** ;
- les fichiers de debug Win64 pour la version **2.7.3.0** ;
- les fichiers de debug Linux 64 bits pour la version **2.7.3.0**.

## À quoi ils peuvent servir

Selon leur contenu exact et le débogueur utilisé, ces fichiers peuvent améliorer :

- la symbolisation d’une pile d’appels ;
- l’identification des fonctions impliquées dans un crash ;
- la comparaison entre une extension native et la version exacte du moteur ;
- le triage d’un problème de chargement de ressources ;
- la recherche d’une régression entre deux versions.

## Ce qu’ils ne fournissent pas

- pas de code source du moteur ;
- pas de garantie de stabilité d’API interne ;
- pas de licence automatique autorisant toute redistribution ;
- pas de remplacement à l’IESDP pour les formats ;
- pas de compatibilité entre symboles et une autre build du binaire.

## Règles d’utilisation

1. Vérifier que la version du binaire correspond exactement aux symboles.
2. Conserver le hash du binaire et du paquet de debug.
3. Séparer les traces issues de 2.6.6.0 et 2.7.3.0.
4. Ne jamais conclure à partir d’un nom de fonction seul : confirmer par la pile, les paramètres observés et un cas reproductible.
5. Ne pas inclure automatiquement les fichiers Beamdog dans la distribution d’un mod ; rediriger vers la page officielle.

## Cas d’usage proche de ton projet

Pour un pipeline de sprites utilisant InfinityLoader ou une extension similaire, ces symboles peuvent aider à localiser un crash de chargement ou de rendu. Ils ne suffisent toutefois pas à prouver qu’un BAM agrandi respecte tous les invariants : la validation des cycles, centres et pages graphiques reste nécessaire.

## Sources
- Portail Beamdog Files: https://files.beamdog.com/
- Debug 2.6.6.0 Win64: https://files.beamdog.com/files/IE_2.6.6.0_Win64_debug.zip
- Debug 2.7.3.0 Win64: https://files.beamdog.com/files/IE_2.7.3.0_Win64_debug.zip
- Debug 2.7.3.0 Linux: https://files.beamdog.com/files/IE_2.7.3.0_Linux_debug.zip
