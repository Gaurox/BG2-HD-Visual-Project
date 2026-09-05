# MonsterIcewind — groupes de dossiers

Les nouveaux membres utilisent :

```text
sprite/families/monster-icewind/<groupe>/<animation-id>-<prefix>-<type>/
```

| Groupe | Types |
|---|---|
| `e0xx-classic-monsters` | cyclopes, ettins, liches, minotaures, momies, trolls, etc. |
| `e2xx-iwd-mixed-creatures` | créatures IWD diverses, géants, dragons, gobelins spéciaux, worgs, etc. |
| `e3xx-ghouls-and-ghosts` | goules, ghasts, fantômes |
| `e4xx-goblins` | gobelins et Khiin |
| `e5xx-lizardfolk` | hommes-lézards |
| `e6xx-myconids` | myconides |
| `e7xx-orogs` | orogs |
| `e8xx-orcs` | orcs |
| `e9xx-salamanders` | salamandres |
| `eaxx-shriekers-and-shadows` | shriekers et ombres |
| `ebxx-skeletons` | squelettes |
| `ecxx-wights` | wights |
| `edxx-yuan-ti` | yuan-ti |
| `eexx-zombies` | zombies |
| `efxx-water-weird` | water weird |

Exemple validé :

```text
e4xx-goblins/e400-mgo1-goblin-axe/
```

La liste des groupes est maintenue dans
`pipeline/scripts/generate_sprite_family_append.py:MONSTER_ICEWIND_GROUPS`.
