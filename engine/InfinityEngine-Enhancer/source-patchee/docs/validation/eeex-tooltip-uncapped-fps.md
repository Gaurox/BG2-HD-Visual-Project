# EEex uncapped-FPS UI tooltip regression

## Status

Open compatibility issue, reproduced and bounded ingame on 2026-08-30. The accepted local
workaround is an EEex presentation limit of 30 FPS. This note does not qualify a renderer or a
release element.

## Environment and symptom

- BG2EE `2.7.3.x`, executable SHA-256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`;
- EEex `1.2.0`;
- prior renderer DLL SHA-256
  `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`;
- renderer INI SHA-256
  `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`;
- engine settings `Tooltips=15` and `Maximum Frame Rate=30`.

With EEex's uncap enabled and no explicit FPS limit, renderer telemetry measured stable presentation
near 154-165 FPS. Hovering any UI button opened its tooltip almost immediately; moving the mouse
over buttons repeatedly recreated or refreshed the tooltip and produced visible flicker. The normal
delayed, stable tooltip behavior was absent.

EEex installs `EEex::Override_uiDrawMenuStack` specifically to normalize the UI-tooltip opening
delay while FPS are uncapped. World tooltips are documented separately in the installed EEex patch
and still follow AI speed. The observed UI behavior is therefore consistent with that normalization
being inactive or repeatedly reset, but the exact failure inside EEex is not yet proven.

## Discriminating tests

### Post-swap map prewarm quarantine — no change

A diagnostic DLL removed the only `hooks::on_post_swap()` calls from both presentation detours and
left the active INI unchanged, including `EnableMapPagePrewarm=true`. At startup it confirmed that
no `CResPVR::Demand` call would be scheduled from the presentation hook. The tooltip defect remained
unchanged ingame.

The candidate DLL was `1,527,808` bytes with SHA-256
`641154854111EF8CFF12530B7E59E6D2D5FF9ECA018A320A193A127BE750A515`. Transaction
`20260830T195522270284Z-264e99a1` restored and verified the exact prior DLL and INI. The experiment's
source diff was also reverted. Map prewarm is not the cause established by this A/B.

### EEex FPS limit — pass

With the prior renderer restored, only these persistent EEex values were added to the active
`Baldur.lua`:

```lua
SetPrivateProfileString('EEex','Uncap FPS Limit Enabled','1')
SetPrivateProfileString('EEex','Uncap FPS Limit','30')
```

The user then confirmed ingame that tooltip delay and stability were restored. `Tooltips=15`, the
renderer DLL and renderer INI were not changed for this comparison.

## Impact on map rendering

The x4 TIS/PVRZ renderer is independent of EEex's presentation rate and remains functional at
30 FPS. The optional map-page prewarm is frame-driven, so the limit changes performance timing but
not eligibility or correctness:

- `MapPagePrewarmDelayFrames=30` starts after about 1 second at 30 FPS versus 0.18 second at
  165 FPS;
- `MapPagePrewarmPagesPerFrame=1` can advance at most 30 pages per second instead of 165 before
  native `Demand` costs and cooldowns;
- missing pages retain the engine's native synchronous fallback.

Do not claim that uncapped FPS are required for x4 maps. A future map-performance campaign must
record the presentation rate because frame-based scheduling makes results at 30 and 165 FPS
non-equivalent.

## Current decision and reopening gate

Keep the local EEex limit at 30 FPS and leave `Tooltips=15` unchanged. Before removing the
workaround:

1. verify the installed EEex hook and `EEex::Override_uiDrawMenuStack` behavior;
2. compare fixed 30 FPS with the display refresh rate using the same menus and mouse path;
3. require a delayed tooltip that remains stable during pointer movement inside one button;
4. rerun the map-prewarm timing gate separately, recording the effective presentation rate.
