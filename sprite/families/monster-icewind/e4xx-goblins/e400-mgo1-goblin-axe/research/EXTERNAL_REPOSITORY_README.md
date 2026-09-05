# Organisation des sprites

```text
sprite/
  families/
    <moteur>/
      <code-famille>-<type-mobs>/
        <animation-id>-<bam-prefix>-<creature>/
          research/
            source/ comparisons/ experiments/
          README.md
```

Règles :

- Utiliser des noms minuscules `kebab-case`.
- Regrouper d'abord par famille moteur, puis par code de famille et type de mobs.
- Un dossier créature représente une identité technique `animation-id + bam-prefix`.
- `research/source/` contient les entrées de référence externes.
- `research/comparisons/` contient les planches de comparaison.
- `research/experiments/` contient les sorties d'essais, séparées par méthode et échelle.
- Ne pas placer de sprites directement à la racine de `sprite/`.
