# Bundled third-party code

`scripts/spellchecker/` is [pyspellchecker](https://github.com/barrust/pyspellchecker) 0.9.1 by Tyler Barrus, MIT licence (`assets/licenses/pyspellchecker-LICENSE.txt`). Its English word-frequency dictionary is in `assets/spell-en.json` (unzipped from the package's `en.json.gz`). It is bundled so the IGPPT spell check works offline and without `pip install`.

Changes from the original:

- `from __future__ import annotations` added to `spellchecker.py` and `utils.py`, the two type aliases in `utils.py` use `typing.Union` instead of `|`, and one `isinstance` check in `spellchecker.py` uses `(str, bytes)`, so it runs on Python 3.9.
- The dictionary is loaded from `assets/spell-en.json` (plain JSON) instead of the package's gzipped resource, because Microsoft 365 Copilot skills do not accept `.gz` files or non-code files in `scripts/`.

Icons in `assets/icons` are from Font Awesome Free (CC BY 4.0).
