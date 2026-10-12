# Known issues — alpha locale BG2 HD

- Windows/Steam x64 uniquement. Linux, Steam Deck et Proton ne sont pas pris en charge par le Core actuel.
- BG2EE Steam 2.7.3.0 et les empreintes EEex/InfinityLoader declarees sont strictement requises. Une mise a jour Steam inconnue est refusee sans ecriture.
- Le renderer fige est maintenant embarque dans l'alpha locale avec rollback
  par empreinte. Son test final de cycle complet sur une installation Steam
  distincte reste requis avant diffusion publique.
- Les droits de redistribution des assets HD restent a approuver : aucune archive produite a ce stade ne doit etre partagee publiquement.
- Les licences MIT du code ne couvrent pas ces assets. Les anciens packages ne sont pas
  retroactivement mis a jour : regenerer un nouveau package avec notices et source WeiDU, puis
  confirmer les dependances du renderer fige avant publication.
- Les 399 variantes maps et les 63 traitements liquides sélectionnés reprennent les QA acquises.
  Réserves esthétiques acceptées : panneaux AR1604 imparfaits, arrondis BC3 AR0506/AR1003/AR1004,
  liseré cyan-vert AR1600, anneaux de pluie discrets AR1000/AR2000. Les conditions météo/pause/cycles
  non observées ailleurs restent non attestées ; qualification combinée sur jeu propre encore requise.
- Les traductions allemande, espagnole, italienne, polonaise, russe, coreenne et chinoise utilisent encore le repli anglais pour les nouvelles chaines et demandent une relecture native avant publication.
- Une verification Steam peut restaurer `Baldur.exe`; utiliser le composant Core pour reparer ou desinstaller le patch, jamais une copie manuelle d'executable.
- Une ancienne sauvegarde qui contient deja des blocs EEex `X-BIV1.0` reste
  potentiellement incompatible avec vanilla. Le correctif est volontairement
  limite aux futures sauvegardes creees depuis un etat compatible vanilla.
- Tant que BG2HD est installe en place, Steam lance la version HD. Pour tester
  cette sauvegarde dans le vrai moteur vanilla, utiliser le retour vanilla
  complet de `Uninstall-BG2HD.exe`, et non une manipulation manuelle des EXE.
