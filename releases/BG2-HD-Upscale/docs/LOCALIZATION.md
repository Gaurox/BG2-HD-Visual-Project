# WeiDU localization

`manifests/languages.json` is authoritative for languages, encoding and review status. English is
loaded first as fallback; the selected TRA is loaded second. The game language and WeiDU language
are independent.

## Change a string

1. Read the current identifiers from `bg2hd/tra/english/setup.tra`.
2. Add the same identifier to every `bg2hd/tra/*/setup.tra` in one change.
3. Keep UTF-8 without BOM and do not renumber existing identifiers.
4. Regenerate TP2/package metadata and run Phase 2.

English and French are reviewed. Languages marked `needs-native-review` in the manifest require
native review before public release. Missing translated keys fall back to English, but they still
violate the project contract that every TRA contains the complete current identifier set.

`HANDLE_CHARSETS` is intentionally unused because this package targets BG2EE only.
