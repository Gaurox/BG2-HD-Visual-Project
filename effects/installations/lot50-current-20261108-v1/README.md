# Lot50 · installé pour test · 2026-11-08

- Demande : installer tout le lot50 et donner les CLUA. Source : `effects/batches/lot50-black-transparent-20261108-v1/production.json`,25SeedVR7B/25xBR4X +Apollo30 ;7corrections noir transparent incluses.
- **Installé/vérifié hors jeu** : `installation.json`, `transaction.json`, `scope-verification.json` ;4294cibles copiées/hashées ; jeu/InfinityLoader fermés. Aucun lancement ni QA ingame déduit.
- Catalogue :638RESREF/66392backings ;538anciens blocs/62500backings préservés ; +50noms natifs/+50companions droits X50N01..50. Registrev3,75cycles animables/150profils once+loop,5164phases par encodage.20656nouveaux contrats passent candidat+installé ; métadonnées28166226octets<32Mio ; INI inchangé.
- DLL/INI/shaders/exécutable/personnages et registres cartes identiques aux snapshots `before.json`. Installation ajoute seulement backings, carriers BAM, VVC de test et catalogue. Ancienne base inclut X28WRTH et correctifs projectiles ; conservée.
- [50CLUA principales](CLUA.md) :Z50T01..50, cycle0 répété ≥4s ; [150profils](CLUA-tous-profils.md), [100comparaisons normal/lumineux](CLUA-transparence.md). Relancer via InfinityLoader, Ctrl+Espace, une commande à la fois ; effets visuels sans dégâts.
-29SPFINODI/31SPFIRET/35SPPFIRAI/36SPPFIRXI/41STEAM1/42STEAM4/50SPOUTA : principaux en alpha normal, noirs transparents corrigés. Autres modes choisis pour revue ; flags natifs,teinte/cadence et usage des vrais sorts non mesurés.15FPS = compatibilité,30FPS cible.
-50lignes CSV : colonnes installation seules actualisées ; production/QA/release et autres lignes préservées. Source et QA acquises des anciens lots inchangées ; QA50 en attente utilisateur.
- Manifest actif : `17839554A2FC5949497D26B2143E3F59F4F320152D933DA48E8127CB0CB82261` ; manifeste précédent `6E11B00001E4EFA49BE9D00E411B2647F97C024FB416996FE11D05B5A876215B` sauvegardé sous `before/`.
- Recette : `pipeline/recipes/effects-lot50-install-20261108-v1/install.py` ; actions `prepare`, `install`, `finish`, `restore`. Restauration ciblée transactionnelle, jeu/loader fermés ; aucune écriture release/payload/staging/TP2/archive.
