"""
@description Wrapper do RapidOCR — reconhece texto chinês numa imagem e devolve caixas.
@connects usado por overlay.worker
"""
from __future__ import annotations

import os
import threading

import numpy as np
from PIL import Image

_engine = None
_lock = threading.Lock()


def _get_engine():
    global _engine
    with _lock:
        if _engine is None:
            # nº de threads do onnxruntime antes de qualquer sessão ser criada
            os.environ.setdefault("OMP_NUM_THREADS", str(min(6, os.cpu_count() or 4)))
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR(
                # legendas nunca estão rotacionadas → dispensa o classificador de ângulo
                use_angle_cls=False,
                # 'max' = reduz a imagem p/ ~960px no maior lado antes de detectar.
                # O default 'min' faz UPSCALE (min lado ≥ 736) e deixa a detecção
                # 5-10× mais lenta em faixas largas. det_model_path='' é obrigatório
                # quando se passa qualquer parâmetro det_ (bug do RapidOCR 1.2.3).
                det_limit_type="max",
                det_limit_side_len=960,
                det_model_path="",
            )
        return _engine


def warmup() -> None:
    """Carrega os modelos ONNX (primeira chamada demora ~2-4 s)."""
    _get_engine()


def _merge_rows(frags: list[dict]) -> list[dict]:
    """Junta fragmentos que estão na mesma linha horizontal num único trecho de texto."""
    frags = sorted(frags, key=lambda f: f["rect"][1])
    rows: list[list[dict]] = []
    for f in frags:
        _, y0, _, y1 = f["rect"]
        cy = (y0 + y1) / 2
        h = y1 - y0
        placed = False
        for row in rows:
            ry0 = min(g["rect"][1] for g in row)
            ry1 = max(g["rect"][3] for g in row)
            if ry0 - h * 0.5 <= cy <= ry1 + h * 0.5:
                row.append(f)
                placed = True
                break
        if not placed:
            rows.append([f])

    merged: list[dict] = []
    for row in rows:
        row.sort(key=lambda g: g["rect"][0])
        xs0 = min(g["rect"][0] for g in row)
        ys0 = min(g["rect"][1] for g in row)
        xs1 = max(g["rect"][2] for g in row)
        ys1 = max(g["rect"][3] for g in row)
        merged.append({
            "text": "".join(g["text"] for g in row),
            "score": sum(g["score"] for g in row) / len(row),
            "rect": (xs0, ys0, xs1, ys1),
        })
    merged.sort(key=lambda m: m["rect"][1])
    return merged


def recognize(img: Image.Image, min_score: float = 0.5, merge: bool = True) -> list[dict]:
    """Retorna [{"text", "score", "rect": (x0, y0, x1, y1)}], ordenado de cima p/ baixo."""
    engine = _get_engine()
    arr = np.array(img.convert("RGB"))
    result, _elapse = engine(arr)

    frags: list[dict] = []
    for item in (result or []):
        box, text, score = item[0], item[1], float(item[2])
        if score < min_score or not str(text).strip():
            continue
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        frags.append({
            "text": str(text).strip(),
            "score": score,
            "rect": (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
        })

    if merge:
        return _merge_rows(frags)
    frags.sort(key=lambda ln: ln["rect"][1])
    return frags
