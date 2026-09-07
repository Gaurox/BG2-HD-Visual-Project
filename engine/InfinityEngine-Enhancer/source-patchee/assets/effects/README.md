# Runtime effects packs

Generated test packs only. Build a new pack from a sealed effect spatial run:

```powershell
python pipeline/scripts/build_effect_runtime_pack.py --resref SPMAGMIS --spatial-run <run-id> --run
```

The game bundle receives this directory as `iee-assets/effects/`. The engine loads only
`EffectAnimations-X4.registry` and its declared `EFX4-*.rgba` files; `README.md` is ignored.
