# Réactivation occlusion native — AR0516

Statut : validée ingame par l'utilisateur le 2026-08-31 sur `planar-test`.

## Identités testées

| Élément | SHA-256 |
|---|---|
| `BaldurReal.exe` 2.7.3.0 | `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57` |
| `InfinityEngine-Enhancer.dll` | `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` |
| INI installé, bridge activé | `EFC6B20059C917982B9F5E110721A19CC72F90567B73A0470F5C02C23D5D0614` |
| `override/AR0516.WED` | `8A0AA3CA4C5D7A9BD42DDD0F55F6CA5ED57241A5F4B141C3CBE7D18D9AA2DB1A` |
| registre runtime AR0516 | `801A3902C7A0A6437A893A79F4DDD5FD05E1810E0F2A1A9F0A319A8CBF01023E` |

Configuration utile : `EnableAreaAnimationX4=true`, `EnableNativeOcclusionBridge=true`,
`EnableNativeOcclusionProbe=false`, `EnableFullFrameSSAA2x=false`.

## Verdict

- `SPHINCT` et `SPHINCT2` repassent derrière les premiers plans WED attendus.
- Le polygone local 49 type `0x09` corrige le premier plan manquant du SPHINCT inférieur.
- Aucun nouveau défaut n'a été signalé pendant le contrôle.
- Installation transactionnelle vérifiée ; transaction locale
  `20260831T202451469598Z-8e700c3b`.

Ce verdict qualifie la combinaison exacte ci-dessus pour AR0516. Il ne qualifie pas le bundle
renderer de release : alpha.5 et alpha.6 précèdent le bridge. L'utilisateur a approuvé
l'intégration manifeste du WED et l'exigence d'un nouveau bundle compatible le 2026-08-31.

Aucun test automatisé, build ou packaging n'a été exécuté pendant cette réactivation.
