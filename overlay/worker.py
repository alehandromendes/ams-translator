"""
@description Thread de trabalho: consome a fila de jobs → OCR → tradução → composição.
@connects criado por overlay.gallery; emite result_ready de volta para a UI
"""
from __future__ import annotations

import queue
import threading
import time
import traceback

from PIL import Image
from PySide6.QtCore import QThread, Signal

from . import compositor, ocr, translator


class TranslateWorker(QThread):
    result_ready = Signal(dict)   # {"id", "original", "translated", "lines", "translated_ok"}
    status = Signal(str)
    queue_size = Signal(int)

    def __init__(self, cfg: dict) -> None:
        super().__init__()
        self.cfg = cfg
        self._q: "queue.Queue[dict | None]" = queue.Queue()
        self._running = True

    def submit(self, job_id: int, img: Image.Image) -> None:
        self._q.put({"id": job_id, "img": img, "mode": "full"})
        self.queue_size.emit(self._q.qsize())

    def retranslate(self, job_id: int, img: Image.Image, lines: list[dict]) -> None:
        """Re-traduz uma captura já feita (ignora o cache), sem refazer o OCR."""
        self._q.put({"id": job_id, "img": img, "mode": "retranslate", "lines": lines})
        self.queue_size.emit(self._q.qsize())

    def stop(self) -> None:
        self._running = False
        self._q.put(None)

    def run(self) -> None:
        self.status.emit("Carregando modelos de OCR…")
        threading.Thread(target=translator.warmup, daemon=True).start()
        try:
            ocr.warmup()
            self.status.emit("Pronto — capture com o atalho ou cole com Ctrl+V.")
        except Exception as e:  # noqa: BLE001
            self.status.emit(f"Falha ao carregar OCR: {e}")

        while self._running:
            job = self._q.get()
            if job is None:
                break
            try:
                self._process(job)
            except Exception as e:  # noqa: BLE001
                traceback.print_exc()
                self.status.emit(f"Erro na captura #{job.get('id')}: {e}")
            finally:
                self.queue_size.emit(self._q.qsize())

    def _process(self, job: dict) -> None:
        job_id, img, mode = job["id"], job["img"], job["mode"]
        src = self.cfg.get("source_lang", "zh-CN")
        tgt = self.cfg.get("target_lang", "pt")

        if mode == "retranslate":
            lines = job["lines"]
            self.status.emit(f"Retraduzindo #{job_id}…")
            force = True
            t_ocr = 0.0
        else:
            self.status.emit(f"OCR na captura #{job_id}…")
            t0 = time.perf_counter()
            lines = ocr.recognize(img, float(self.cfg.get("min_ocr_score", 0.5)))
            t_ocr = time.perf_counter() - t0
            force = False
            if not lines:
                self.status.emit(f"#{job_id}: nenhum texto reconhecido ({t_ocr:.1f}s)")
                self.result_ready.emit({
                    "id": job_id, "original": img, "translated": img,
                    "lines": [], "translated_ok": True,
                })
                return
            self.status.emit(f"Traduzindo #{job_id} ({len(lines)} linha(s))…")

        t1 = time.perf_counter()
        pts, ok = translator.translate_lines(
            [ln["text"] for ln in lines], source=src, target=tgt, force=force
        )
        t_tr = time.perf_counter() - t1

        pairs = [
            {"rect": ln["rect"], "cn": ln["text"], "pt": pt, "score": ln.get("score", 1.0)}
            for ln, pt in zip(lines, pts)
        ]
        translated = compositor.compose(img, pairs, self.cfg.get("font_path"))
        self.result_ready.emit({
            "id": job_id, "original": img, "translated": translated,
            "lines": pairs, "translated_ok": ok,
        })
        if ok:
            extra = f"OCR {t_ocr:.1f}s + " if mode == "full" else ""
            self.status.emit(f"Captura #{job_id} pronta  ·  {extra}tradução {t_tr:.1f}s")
        else:
            self.status.emit(
                f"#{job_id}: tradução FALHOU — {translator.last_error[:400]}  "
                "(clique em ↻ Retraduzir)"
            )
