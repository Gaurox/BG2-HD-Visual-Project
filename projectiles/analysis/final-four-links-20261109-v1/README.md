# Quatre derniers raccords installés —2026-11-09

- HLYMITE/SHAIR/SHEARTH/SPSCORIC ajoutés au scopeFX existant ;0nouvelle adresse/hook,0image/PRO/registre modifié.
- [CLUA réduits](CLUA.md) :**3variantes colorées uniquement**. HLYMITE rouge194,SHAIR4/130,SHEARTH6/137. Neutres65/118/119 vérifiés automatiquement ;SPSCORIC conserve l'accord visuel antérieur avec qualification statique des9cycles,aucun nouveau tir demandé.
- `qualification.json` :830backings installés exacts(SHA),12cycles natifs,1776contrats base/once/casse/dimensions/centres. Registre743ressources/72563textures inchangé.
- `source-palettes.json` :sources natives+SHAIR4/SHEARTH6.BMP figés ;`effect_native_projectile_palettes.h` lie les palettes3BAM à leursSHA. SHAIR/SHEARTH255RGB uniques ;HLYMITE3pairesRGB dupliquées.
- `effect_indexed_palette.h` :choix des nœuds par ressource ;transfertRGB depuis la palette **réellement réalisée pour la cellule** ;empreinteGPU séparant source/couleur/opacité. Écriture uniquement dans la copie d'upload ;source/cacheCPU inchangés. HLYMITE :ambiguïté des indices dupliqués oualpha non uniforme→repli natif. Noir additif neutre conservé. SHAREA conserve ses nœuds/empreintes/règles antérieurs.
- Tests :765nœudsRGB exacts pourSHAIR4,SHEARTH6 etune réalisationrougeHLYMITE ;identité neutre,RGBA/BGRA,alpha,ambiguïté HLYMITE ;WGL upload/cache entre familles/retour neutre ;anciennes palettesSHAREA inchangées.5/5suites passent.
- `before-install-native-loader.log` et `installed-native-loader.log` :1776contrats passants chacun,0lectureRGBA par le probe metadata. Aucun dessinHD live inventé.
- Installation transactionnelle : `engine/InfinityEngine-Enhancer/installations/projectiles-final-four-links-20261109-v1/installation.json`. DLL+seuleclétraceINI ;backups,catalogue/PRO/shaders/sprites protégés ;QA acquises etrelease conservées.
- `visual-tests.json` lie les3pilotes natifs aux capacités/SHA ;aucun helper synthétique installé. Après retour etlecturelogs,jeu/loader arrêtés,désactiver uniquementEnableEffectStreamingTrace avec `install.py disable-trace`.
- Les10omissions de scope repérées dans la passe native sont maintenant raccordées statiquement/installées(6déjà observéesHD+4ce lot). Ce constat n'accorde pas une QA globale243 ni une observationHD encore absente.
