# Préparation hors frame des pages de carte

Contrat courant de `MAP-PERF-001`. Le goulot mesuré est l'appel synchrone indivisible
`CResPVR::Demand`. La phase B2f prépare un seul candidat JIT sur worker, puis permet au thread de
rendu de substituer au plus quatre buffers décodés à la frontière zlib manifestée. Elle est
désactivée par défaut et non qualifiée release.

## Frontière sûre

- Le worker lit seulement une PVRZ locale explicitement prise en charge.
- Il valide enveloppe, flux zlib unique, taille décodée, header PVR v3 et payload DXT1/DXT5.
- Il ne touche jamais OpenGL, WGL, objet moteur, allocateur moteur ni `CResPVR::Demand`.
- Le thread de rendu copie un buffer exactement apparié dans la destination déjà allouée par le
  moteur à `CResPVR::Demand+0x15F`, puis reprend le code natif à `+0x164`.
- Cache 128 entrées, création/upload GL, publication, éviction et libération restent natifs.
- Tout écart d'identité, de génération, de taille, de CRC ou de disponibilité appelle le zlib
  original.

## Ownership et bornes

- un worker joignable, priorité inférieure, aucun thread détaché ;
- jobs et résultats à capacité fixe, doublons coalescés ;
- identités copiées : génération, zone, tileset, page et numéro ;
- buffers immuables transférés par ownership, jamais pointeurs moteur empruntés ;
- annulation au changement de zone/contexte, disable, shutdown ou premier élargissement de vue ;
- retirement explicite du lecteur avant tout fallback natif sur la même page ;
- aucune exception au-delà d'un hook ou d'une entrée de thread.

Bornes du parser/probe : 32 Mio compressés et 20 Mio décodés par page, 96 jobs, quatre résultats et
72 Mio de handoff agrégé. B2f n'utilise qu'un slot utile à la fois et quatre revendications par
génération.

## Configuration

Le prototype exige :

```ini
[Core]
PerformanceLogs = true
EnableMapPageOffframeProbe = true
EnableMapPageOffframeConsume = true
```

Les valeurs par défaut restent `false`. Une cible sans manifeste exact ou preuve requise conserve
le chemin natif.

## Preuves et gate suivante

La chaîne B0→B2f est conservée, sans réécriture, dans [`validation/`](validation/). La preuve
courante est [`map-page-offframe-phase3b2f.md`](validation/map-page-offframe-phase3b2f.md) : un
passage AR0700N/AR0516/AR0602/AR0900, seize revendications réussies, sans erreur. Ce passage unique
n'est pas statistique.

Avant qualification :

1. campagnes A/B répétées et contrebalancées sur les quatre zones ;
2. binaire final et télémétrie figée ;
3. campagne distincte avec cache OS froid ;
4. vérification visuelle, stabilité, latence et fallback natif ;
5. installation/restauration par reçu renderer neuf.

Le rapport de suivi projet reste [`../../../../pipeline/PROBLEMES_A_RESOUDRE.md`](../../../../pipeline/PROBLEMES_A_RESOUDRE.md).
