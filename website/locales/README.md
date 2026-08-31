# Localization

The site ships in English (site root) and French (`fr/`), as a mirrored static
page set with identical layout and structure:

```text
index.html      fr/index.html
progress.html   fr/progress.html
gallery.html    fr/gallery.html
```

- Both language sets share `assets/` (CSS, JS, images, comparisons). Pages under
  `fr/` reference them with `../assets/...`.
- The header `EN / FR` control links each page to its counterpart in the other
  language; the active language is marked with `aria-current="page"`.
- Each page declares `<html lang="…">` and `<link rel="alternate" hreflang="…">`
  for its EN/FR pair.
- `assets/js/site.js` picks a few runtime strings (nav-toggle label, dialog
  fallback) from `document.documentElement.lang`.

To add another language, mirror the three pages into a new `xx/` directory,
point its asset links at `../assets/`, translate the copy, and add the matching
`hreflang` links and switch entries on every page.
