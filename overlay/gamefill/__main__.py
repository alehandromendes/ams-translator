"""
@description CLI: `python -m overlay.gamefill [opções]`
@connects overlay.gamefill.core
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import DIALOGUE_MODULES, GameFill, find_mod_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m overlay.gamefill",
        description="Preenche as linhas de diálogo que o mod de localização de "
                    "Lord of Mysteries deixou em chinês.",
    )
    ap.add_argument("--mod-dir", help="caminho do .../C7/Saved/Mods/localization "
                                      "(autodetecta se omitido)")
    ap.add_argument("--modules", nargs="+", metavar="MOD",
                    help="sobrescreve a lista de módulos (nomes de arquivo, sem .lua)")
    ap.add_argument("--all-modules", action="store_true",
                    help="todos os StringDB, não só os de diálogo")
    ap.add_argument("--dry-run", action="store_true",
                    help="mostra o que faria, sem gravar nada no jogo")
    ap.add_argument("--restore", action="store_true",
                    help="desfaz: remove o overlay e volta os índices originais")
    ap.add_argument("--no-mark", action="store_true",
                    help="não põe o prefixo » nas linhas preenchidas")
    ap.add_argument("--mark", default="» ",
                    help="prefixo das linhas preenchidas (padrão: '» ')")
    args = ap.parse_args(argv)

    mod_dir = find_mod_dir(args.mod_dir)
    if not mod_dir:
        print("!! não achei .../C7/Saved/Mods/localization/bootstrap.lua\n"
              "   passe --mod-dir <caminho>", file=sys.stderr)
        return 2
    print(f"mod: {mod_dir}")

    mark = "" if args.no_mark else args.mark
    gf = GameFill(mod_dir, mark=mark)

    if args.restore:
        undone = gf.restore()
        print(f"restaurado: {len(undone)} módulo(s) -> {', '.join(undone) or '(nada)'}")
        return 0

    if args.all_modules:
        modules = sorted({p.stem for p in gf.ld_dir.glob("StringDB_CN_Data*.lua")})
    else:
        modules = args.modules or DIALOGUE_MODULES

    report = gf.run(modules, write=not args.dry_run)

    print(f"\n{'(dry-run) ' if args.dry_run else ''}resumo:")
    for m in report.modules:
        if not m.total_cjk:
            continue
        print(f"  {m.module:34}  CJK {m.total_cjk:>4}  "
              f"preench. {m.filled:>4}  reaproveit. {m.reused:>4}  "
              f"ainda c/ chinês {m.residual:>3}")
    print(f"\n  total: {report.total_cjk} strings com chinês, "
          f"{report.total_filled} preenchidas, "
          f"{report.total_residual} ainda precisam de revisão")
    if not report.provider_ok:
        print("  ⚠  tradução online falhou em parte — rode de novo com internet")
    if not args.dry_run:
        print(f"\n  relatório: {Path(gf.state_path).parent / 'report.csv'}")
        print("  revise as linhas marcadas »? no jogo; regenere com "
              "`python -m overlay.gamefill`, desfaça com `--restore`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
