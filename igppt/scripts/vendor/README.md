# Bundled third-party code

`spellchecker/` is [pyspellchecker](https://github.com/barrust/pyspellchecker) 0.9.1 by Tyler Barrus, MIT licence (see `spellchecker/LICENSE`).
Only the English dictionary is included. It is bundled so the IGPPT spell check works offline and without `pip install`.

Changes from the original, so it runs on Python 3.9: `from __future__ import annotations` added to `spellchecker.py` and `utils.py`, the two type aliases in `utils.py` use `typing.Union` instead of `|`, and one `isinstance` check in `spellchecker.py` uses `(str, bytes)`.
