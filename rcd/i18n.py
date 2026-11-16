"""Bilingual text helper. All user-facing strings produced by the engines are {pl, en} dicts."""


def L(pl, en=None):
    return {"pl": pl, "en": en if en is not None else pl}


def tr(x, lang="pl"):
    if isinstance(x, dict) and "pl" in x:
        return x.get(lang) or x.get("pl")
    return x if x is not None else ""
