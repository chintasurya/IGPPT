"""Text rules for IGPPT decks: dashes, spacing, placeholders and spelling.

Shared by validate.py (checks the finished deck) and make_deck.py (checks and auto-fixes the spec).

    problems = check_text("Ticket volume is faling — fast")   # [(level, message), ...]
    fixed, changes = fix_text("Results — strong")              # mechanical fixes only

Spelling uses the bundled pyspellchecker (scripts/spellchecker, MIT licence; dictionary in assets/spell-en.json)
plus two word lists:
  assets/wordlist.txt   business and technology terms that ship with the skill
  igppt-words.txt       optional, next to the spec or in the project folder: client names, product names
British spellings (colour, organisation, prioritise, centre) are accepted.
"""
import re
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FAIL, WARN = "FAIL", "WARN"

# ---------------------------------------------------------------- dashes and spacing
EM_DASHES = "—―"            # em dash, horizontal bar
EN_DASH = "–"
_RANGE = re.compile(r"(?<=[0-9A-Za-z%$])\s*[–—―]\s*(?=[0-9$])")   # 9–5, Q1–Q2, $5–$10
_SPACED = re.compile(r"\s+[–—―]\s+|\s*--\s*")                      # word — word, word -- word
_TIGHT = re.compile(r"(?<=\w)[–—―](?=\w)")                         # word—word
_ANY_DASH = re.compile(r"[–—―]|--")
PLACEHOLDER_FAIL = re.compile(r"lorem ipsum|click to (add|edit)|\bTODO\b|\bFIXME\b|\binsert (text|title|here)\b", re.I)
INTERNAL = re.compile(r"(?:^|[.;!?]\s+|\n)\s*(audience|target audience|presenter|presenter notes?|speaker notes?|"
                      r"talking points?|notes? to self|note for (?:the )?(?:presenter|team)|internal(?: only| note)?|"
                      r"for internal use|do not show|instructions?|prompt)\s*:", re.I)
PLACEHOLDER_WARN = re.compile(r"\[[^\]]{0,40}\]|\bTBD\b|\bXX+\b|\?\?")


def fix_text(text):
    """Mechanical fixes that never change meaning. Returns (new_text, [description, ...])."""
    if not isinstance(text, str):
        return text, []
    new, changes = text, []
    if _ANY_DASH.search(new):
        new = _RANGE.sub("-", new)                 # number ranges keep a plain hyphen
        new = _SPACED.sub(", ", new)               # a spaced dash between words becomes a comma
        new = _TIGHT.sub("-", new)
        new = new.replace("—", ", ").replace("―", ", ").replace("–", "-")
        new = re.sub(r",\s*,", ",", new).replace(" ,", ",")
        new = re.sub(r"^,\s*|,\s*$", "", new)
        new = re.sub(r",\s*([.:;!?])", r"\1", new)
        changes.append("replaced dashes")
    squeezed = re.sub(r"(?<=\S) {2,}(?=\S)", " ", new).strip()
    if squeezed != new:
        new = squeezed
        changes.append("removed extra spaces")
    return new, changes


# ---------------------------------------------------------------- spelling
_spell = None
spell_error = None
_known = set()
_extra_loaded = set()
_TOKEN = re.compile(r"[A-Za-z][A-Za-z'’]*")
_URL = re.compile(r"\S+@\S+|https?://\S+|www\.\S+|\S+\.(com|org|net|io|ai|gov|edu)\b\S*", re.I)
_UK = [("isations", "izations"), ("isation", "ization"), ("ising", "izing"), ("ised", "ized"), ("ises", "izes"),
       ("ise", "ize"), ("ysing", "yzing"), ("ysed", "yzed"), ("yse", "yze"), ("ours", "ors"), ("our", "or"),
       ("ourable", "orable"), ("ourite", "orite"), ("tres", "ters"), ("tre", "ter"), ("ences", "enses"),
       ("ence", "ense"), ("ogues", "ogs"), ("ogue", "og"), ("mmes", "ms"), ("mme", "m"), ("lled", "led"),
       ("lling", "ling"), ("eable", "able"), ("lement", "lment")]


def _load_spellchecker():
    """pyspellchecker 0.9.1 (MIT) is bundled in scripts/spellchecker and its English dictionary in
    assets/spell-en.json, so the spell check works offline and needs no pip install."""
    global _spell
    if _spell is not None:
        return _spell
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:
        sys.path.insert(0, here)
    global spell_error
    try:
        from spellchecker import SpellChecker
        _spell = SpellChecker(language=None, local_dictionary=str(ASSETS / "spell-en.json"), distance=2)
    except Exception as e:  # report why, instead of silently skipping the spell check
        spell_error = f"{type(e).__name__}: {e}"
        _spell = False
        return _spell
    load_words(ASSETS / "wordlist.txt")
    return _spell


def load_words(path):
    """Add a word list (one word or phrase per line, # for comments) to the known words."""
    path = Path(path)
    if not path.is_file() or path in _extra_loaded:
        return
    _extra_loaded.add(path)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        for w in re.split(r"[\s/]+", line):
            if w:
                _known.add(w.lower().strip("'’"))


def spelling_available():
    return bool(_load_spellchecker())


def _known_word(sp, w):
    if w in _known or w in sp:
        return True
    for uk, us in _UK:                              # British spelling of a known US word
        if w.endswith(uk) and (w[: -len(uk)] + us) in sp:
            return True
    for suffix in ("s", "es", "'s", "’s", "ed", "ing", "er", "ers"):
        if w.endswith(suffix) and (w[: -len(suffix)] in _known):
            return True
    return False


def misspellings(text):
    """[(level, word, suggestion)] for words that look misspelt. FAIL = a likely typo of a common word,
    WARN = an unknown word (often a name or product): confirm it or add it to igppt-words.txt."""
    sp = _load_spellchecker()
    if not sp:
        return []
    out = []
    for raw in _TOKEN.findall(_URL.sub(" ", text)):
        word = raw.strip("'’")
        if len(word) < 3 or any(ch.isdigit() for ch in word):
            continue
        if word.isupper() or re.search(r"[a-z][A-Z]", word):        # acronyms (SLA, QBR) and CamelCase (ServiceNow)
            continue
        w = word.lower().replace("’", "'")
        if w.endswith("'s"):
            w = w[:-2]
        if _known_word(sp, w):
            continue
        cand = sp.correction(w)
        if cand and cand != w and sp.word_usage_frequency(cand) >= 1e-6:
            out.append((FAIL, word, cand))
        else:
            out.append((WARN, word, cand if cand and cand != w else None))
    return out


def check_text(text, spelling=True):
    """All rules for one piece of slide text. Returns [(level, message)]."""
    probs = []
    if not isinstance(text, str) or not text.strip():
        return probs
    if re.search(f"[{EM_DASHES}]", text):
        probs.append((FAIL, "contains an em dash (—); use a comma, colon or full stop"))
    if EN_DASH in text:
        probs.append((FAIL, "contains an en dash (–); use a hyphen for ranges or a comma between clauses"))
    if "--" in text:
        probs.append((FAIL, "contains a double hyphen (--)"))
    if re.search(r"\S  +\S", text):
        probs.append((WARN, "has double spaces"))
    m = re.search(r"\b(\w+)\s+\1\b", text, re.I)
    if m and not m.group(1).isdigit() and m.group(1).lower() not in ("had", "that", "bye", "very", "so", "no"):
        probs.append((FAIL, f"repeated word '{m.group(0)}'"))
    m = INTERNAL.search(text)
    if m:
        probs.append((FAIL, f"internal or presenter note shown on the slide ('{m.group(1)}:'); move it to the speaker "
                            f"notes (\"notes\"), not the on-slide \"note\""))
    m = PLACEHOLDER_FAIL.search(text)
    if m:
        probs.append((FAIL, f"leftover placeholder text '{m.group(0)}'"))
    m = PLACEHOLDER_WARN.search(text)
    if m:
        probs.append((WARN, f"placeholder '{m.group(0)}' still to be filled in"))
    if spelling:
        for level, word, cand in misspellings(text):
            if level == FAIL:
                probs.append((FAIL, f"spelling: '{word}' (did you mean '{cand}'?)"))
            else:
                hint = f" (closest: '{cand}')" if cand else ""
                probs.append((WARN, f"unknown word '{word}'{hint}: check it, or add it to igppt-words.txt if it is a name or term"))
    return probs
