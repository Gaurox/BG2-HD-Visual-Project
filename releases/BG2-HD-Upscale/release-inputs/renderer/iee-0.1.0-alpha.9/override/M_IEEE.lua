-- BG2HD is graphics-only. EEex 1.2.0's extended creature marshalling writes
-- X-BIV1.0 records that the vanilla engine cannot unmarshal. Keep the HD
-- runtime save-neutral so new save chains remain loadable without EEex.
EEex_Debug_DisableExtraCreatureMarshalling = true

EEex_DisableCodeProtection()
EEex_InitLuaBindings("InfinityEngine-Enhancer")
EEex_EnableCodeProtection()
