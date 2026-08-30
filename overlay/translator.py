"""
@description Tradução CN→PT sem chave de API. Todas as linhas de uma captura vão numa
             única requisição (batch). Ordem de provedores: clients5 (Google/extensão),
             MyMemory, gtx. Lembra qual funcionou por último e tenta esse primeiro.
             Cache em disco + pré-substituição de nomes próprios pelo glossário.
@connects usado por overlay.worker; reaproveita glossary/*.csv e data/cache/
"""
from __future__ import annotations

import csv
import json
import os
import re
import threading

import requests

from .config import BUNDLE_DIR, CACHE_PATH, DATA_DIR, GLOSSARY_DIR

_CJK = re.compile(r"[一-鿿]")
_lock = threading.Lock()
_cache: dict | None = None

_TIMEOUT = (4, 9)            # (conexão, leitura)
_SEP = "\n"

last_error: str = ""        # motivo da última falha total (lido pelo worker)


def _ca_bundle():
    """Caminho do bundle de CAs — tolerante ao empacotamento do PyInstaller."""
    candidates = [BUNDLE_DIR / "cacert.pem", DATA_DIR / "cacert.pem"]
    try:
        import certifi

        candidates.append(certifi.where())
    except Exception:  # noqa: BLE001
        pass
    for c in candidates:
        try:
            if os.path.isfile(str(c)):
                return str(c)
        except Exception:  # noqa: BLE001
            pass
    return True   # sem bundle próprio → deixa o requests/OpenSSL decidir


_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
_CA = _ca_bundle()
_SESSION.verify = _CA
if isinstance(_CA, str):
    os.environ.setdefault("SSL_CERT_FILE", _CA)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA)
# respeita proxy do sistema mesmo rodando elevado
try:
    _SESSION.trust_env = True
except Exception:  # noqa: BLE001
    pass


# ----------------------------------------------------------------------
# cache
# ----------------------------------------------------------------------
def _load_cache() -> dict:
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            _cache = {}
    return _cache


def _save_cache() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(_cache, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# ----------------------------------------------------------------------
# glossário
# ----------------------------------------------------------------------
def _load_glossary() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for path in sorted(GLOSSARY_DIR.glob("*.csv")):
        try:
            with path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    cn = (row.get("cn") or "").strip()
                    pt = (row.get("pt_br") or "").strip()
                    if cn and pt and _CJK.search(cn):
                        pairs.append((cn, pt))
        except Exception:  # noqa: BLE001
            pass
    pairs.sort(key=lambda p: len(p[0]), reverse=True)  # mais longo primeiro
    return pairs


_GLOSSARY = _load_glossary()


def _pre_substitute(text: str) -> str:
    for cn, pt in _GLOSSARY:
        if cn in text:
            text = text.replace(cn, f" {pt} ")
    return text


def _clean(s: str) -> str:
    return re.sub(r"[ \t]{2,}", " ", (s or "")).strip()


# ----------------------------------------------------------------------
# provedores (sem chave) — recebem list[str], devolvem list[str] alinhada ou None
# ----------------------------------------------------------------------
class _HttpError(Exception):
    pass


def _clients5(texts: list[str], source: str, target: str) -> list[str] | None:
    sl = "auto" if source in ("auto", "zh-CN", "zh") else source
    params = [("client", "dict-chrome-ex"), ("sl", sl), ("tl", target)]
    params += [("q", t) for t in texts]
    r = _SESSION.get("https://clients5.google.com/translate_a/t", params=params, timeout=_TIMEOUT)
    if r.status_code != 200:
        raise _HttpError(f"clients5 HTTP {r.status_code}")
    data = r.json()
    if len(texts) == 1:
        if isinstance(data, list) and data:
            if isinstance(data[0], list):
                return ["".join(s[0] for s in data if s and s[0])]
            if isinstance(data[0], str):
                return [data[0]]
        return None
    out: list[str] = []
    for item in data:
        if isinstance(item, list) and item:
            out.append(str(item[0]))
        elif isinstance(item, str):
            out.append(item)
    return out if len(out) == len(texts) else None


def _gtx(texts: list[str], source: str, target: str) -> list[str] | None:
    r = _SESSION.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": _SEP.join(texts)},
        timeout=_TIMEOUT,
    )
    if r.status_code != 200:
        raise _HttpError(f"gtx HTTP {r.status_code}")
    data = r.json()
    full = "".join(seg[0] for seg in data[0] if seg and seg[0])
    parts = full.split(_SEP)
    if len(parts) == len(texts):
        return parts
    return [full] if len(texts) == 1 else None


def _lingva(texts: list[str], source: str, target: str) -> list[str] | None:
    import urllib.parse

    sl = "zh" if source in ("auto", "zh-CN", "zh") else source.split("-")[0]
    tl = target.split("-")[0]        # lingva usa 'zh', não 'zh-CN'
    out: list[str] = []
    for host in ("https://lingva.ml", "https://translate.plausibility.cloud"):
        try:
            for t in texts:
                r = _SESSION.get(
                    f"{host}/api/v1/{sl}/{tl}/{urllib.parse.quote(t, safe='')}",
                    timeout=_TIMEOUT,
                )
                if r.status_code != 200:
                    raise _HttpError(f"lingva HTTP {r.status_code}")
                out.append(r.json().get("translation") or t)
            return out
        except Exception:  # noqa: BLE001
            out = []
            continue
    return None


def _mymemory(texts: list[str], source: str, target: str) -> list[str] | None:
    tgt = "pt-BR" if target == "pt" else target
    src = "zh-CN" if source in ("auto", "zh") else source
    r = _SESSION.get(
        "https://api.mymemory.translated.net/get",
        params={"q": _SEP.join(texts), "langpair": f"{src}|{tgt}"},
        timeout=_TIMEOUT,
    )
    if r.status_code != 200:
        raise _HttpError(f"mymemory HTTP {r.status_code}")
    t = (r.json().get("responseData") or {}).get("translatedText") or ""
    parts = t.split(_SEP)
    if len(parts) == len(texts):
        return parts
    return [t] if len(texts) == 1 else None


_PROVIDERS: list[tuple[str, callable]] = [
    ("clients5", _clients5),
    ("mymemory", _mymemory),
    ("lingva", _lingva),
    ("gtx", _gtx),
]
_preferred = "clients5"


def _translate_uncached(texts: list[str], source: str, target: str) -> list[str] | None:
    """None = todos os provedores falharam (last_error explica)."""
    global _preferred, last_error
    order = sorted(_PROVIDERS, key=lambda p: 0 if p[0] == _preferred else 1)
    errors: list[str] = []
    for name, fn in order:
        try:
            res = fn(texts, source, target)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {type(e).__name__} {e}".strip())
            res = None
        if res and len(res) == len(texts) and any(x and x.strip() for x in res):
            _preferred = name
            last_error = ""
            return [_clean(x) or orig for x, orig in zip(res, texts)]
    last_error = " | ".join(errors) or "sem resposta dos provedores"
    return None


def warmup() -> None:
    """Abre a conexão TLS com o provedor pra 1ª tradução real não pagar o handshake."""
    try:
        _clients5(["你好"], "auto", "pt")
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------
def translate_lines(
    texts: list[str], source: str = "zh-CN", target: str = "pt", force: bool = False
) -> tuple[list[str], bool]:
    """Retorna (traduções, ok). ok=False → todos os provedores falharam
    (traduções = texto original, e nada é gravado no cache pra permitir retry)."""
    cache = _load_cache()
    out: list[str | None] = [None] * len(texts)
    miss_idx: list[int] = []
    miss_txt: list[str] = []

    for i, original in enumerate(texts):
        hit = None if force else cache.get(f"{source}|{target}|{original}")
        if hit is not None:
            out[i] = hit
        else:
            miss_idx.append(i)
            miss_txt.append(_pre_substitute(original))

    ok = True
    if miss_txt:
        translated = _translate_uncached(miss_txt, source, target)
        if translated is None:
            ok = False
            for i in miss_idx:
                out[i] = texts[i]           # devolve original, NÃO cacheia
        else:
            for i, tr in zip(miss_idx, translated):
                out[i] = tr
                cache[f"{source}|{target}|{texts[i]}"] = tr
            with _lock:
                _save_cache()

    return [o if o is not None else "" for o in out], ok


def translate_text(text: str, source: str, target: str) -> tuple[str, bool]:
    """Tradução livre de UM texto em qualquer direção (ex.: PT → zh-CN).
    Sem substituição de glossário. Retorna (tradução, ok)."""
    text = (text or "").strip()
    if not text:
        return "", True
    cache = _load_cache()
    key = f"{source}|{target}|{text}"
    hit = cache.get(key)
    if hit is not None:
        return hit, True
    res = _translate_uncached([text], source, target)
    if res is None:
        return text, False
    out = _clean(res[0]) or text
    cache[key] = out
    with _lock:
        _save_cache()
    return out, True
