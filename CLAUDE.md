# CLAUDE.md — AMS Translator

> Carregado em toda sessão. App standalone PySide6 que traduz legendas/textos de jogos pra PT-BR.
> Repo: `github.com/alehandromendes/ams-translator` (renomeado de `tradutor-legendas`).
> Biblioteca de traduções: `github.com/alehandromendes/ams-translator-traducoes` (pasta local `C:/DEV/ams-translator-traducoes/`).

---

## ⛔ REGRAS ABSOLUTAS

1. **NENHUM scan, dump, varredura de diagnóstico ou escrita em disco roda no jogo em produção.**
   - Qualquer captura de faltas (`scan_capture`, `scan_cn`, `_G.__adv`), dump (`do_dump`, `_catalog.txt`) ou status (`write_apply_status`, `_loaded.txt`, `_menu_probe.txt`, `_cn_misses.txt`, `_scan_misses.txt`) **SÓ pode executar com `H._dev` verdadeiro** (marcador `Saved/Mods/lua/_tl_dump/.dev` ou `/run`, criados só na máquina de dev).
   - "Status de dump" (o `apply_status.txt`) também é **só dev**.
   - Em produção o único trabalho contínuo permitido no hotpatch é a **varredura de tradução** (sweep EN→PT) — e ela é limitada por orçamento de nós + backoff quando ociosa. Nada de I/O, nada de `debug.getupvalue` em loop, nada perpétuo sem limite.
   - Toda vez que adicionar código no `hotpatch.lua`/`Init.lua`, **auditar**: isso roda todo tick? tem limite? escreve em disco? Se sim e não for a tradução em si → `if H._dev`.

2. **NUNCA modificar arquivo do CPDD English patch.** O mod (`tl_translate`) só escreve em `Saved/Mods/lua/mods/tl_translate/`, `Saved/Mods/lua/cpdd_user_settings.lua` e `Saved/Mods/lua/_tl_dump/` (dev). Nunca tocar `Saved/Mods/lua/mods/cpdd_runtime_fixes/`, `bootstrap.lua`, `.pak`, fontes customizadas.

3. **NUNCA redistribuir o CPDD.** O app só baixa o instalador OFICIAL da release do Lani27 (`Lani27/lord-of-mysteries-english-patch`). Não hospedar.

4. **NUNCA commitar segredos.**

5. **NUNCA travar/crashar o jogo.** Traduzir string que o jogo usa como enum/estado quebra a lógica (ex.: `NewHeadInfo.lua:436 attempt to index nil`). Palavras curtas soltas (`Loading`, `Server`, `Exit`, `Level`, `HP`, `type`, `nodeType`) ficam no `SKIP`/fora do `OVR`. Só rótulos de UI inequívocos.

6. **`.exe` é multi-jogo — nada de jogo específico embutido.** `Init.lua`, `hotpatch.lua`, `cpdd_user_settings.lua` e toda a camada de tradução são BAIXADOS do repo de traduções (`translations_index.json` `files[]` com `dest` por arquivo). `overlay.spec` NÃO empacota `luamod/` nem `prebuilt/` (só fallback dev).

---

## 🛠️ COMANDOS

```bash
cd C:/DEV/tradutor-legendas

# Rodar do código
.venv/Scripts/python.exe -m overlay

# Validar Lua (o venv tem lupa)
.venv/Scripts/python.exe -c "import lupa; lupa.LuaRuntime().compile(open('overlay/gamefill/luamod/hotpatch.lua',encoding='utf-8').read())"

# Build do .exe  (fecha o .exe aberto antes — uac_admin, taskkill não-elevado falha)
.venv/Scripts/python.exe -m PyInstaller --noconfirm overlay.spec   # -> dist/AMS Translator/

# Build do instalador (ISCC ~2-3 min comprimindo — esperar ISCC.exe sair, não só o arquivo existir)
"$LOCALAPPDATA/Programs/Inno Setup 6/ISCC.exe" installer/ams-translator.iss   # -> installer/Output/AMSTranslatorSetup.exe

# Deploy/teste numa pasta de jogo (dev)
.venv/Scripts/python.exe -m overlay.gamefill.gamepatch <status|install|restore> "C:/Jogos/Game/C7"

# Regenerar a memória de tradução EN->PT (_en2pt_*.lua) — traduz o inglês do CPDD
.venv/Scripts/python.exe -m overlay.gamefill.patch_pt [--status | --restore]
```

**Critério de pronto:** `lupa` compila o Lua + `.venv/Scripts/python.exe -c "import overlay.game_translate"` sem erro. Para mudança de Python: rebuild do `.exe`. Para mudança de `hotpatch.lua`/`Init.lua`/dados: só sync pro repo de traduções (o app baixa).

---

## 🏗️ ARQUITETURA

```
overlay/                 pacote Python (o app)
  gallery.py             janela principal (captura ao vivo, galeria)
  game_translate.py      diálogo "Tradução de jogos" (Procurar/Baixar/Instalar/Restaurar/Verificar)
  translator.py          tradução sem chave (clients5 -> gtx -> MyMemory)
  config.py              overlay_config.json em %LOCALAPPDATA%\AMS Translator (com migração do nome antigo)
  gamefill/
    library.py           lê translations_index.json (GitHub -> fallback embutido), baixa files[], instala
    gamepatch.py         install()/restore() — restaura CPDD + deploy do mod a partir do baixado
    patch_pt.py          gera _en2pt_*.lua (dev); _MENU_LABELS = fonte da verdade dos rótulos do menu ESC
    translations_index.json   índice embutido (fallback) — 107 files[] pro LOTM
    luamod/              Init.lua + hotpatch.lua + cpdd_user_settings.lua (fallback DEV; ship = repo de traduções)
    prebuilt/            104 pt/*.lua (gitignored; fallback dev)
installer/ams-translator.iss   Inno Setup — AppName "AMS Translator", uninstall pergunta se apaga dados
download/AMSTranslatorSetup.exe (Git LFS)
```

### Mod `tl_translate` (o que roda dentro do jogo)
- **`Init.lua`** — carregado pelo `LOMModLoader` do CPDD via `cpdd_user_settings.lua` (`PersonalLoad`). Faz `apply` (mescla `pt/<modulo>.lua` nos dados do StringDB), wrap de `GetLangStr`/`GetRow` (traduz retorno), injeta `Loader.ExternalLoaded["cpdd_translation.*"]`, e chama `hotpatch.lua` a cada `HP_EVERY` calls de getter (dev 300 / **produção 900**, chunk cacheado).
- **`hotpatch.lua`** — varredura runtime: `OVR` (rótulos curados), `MENU_PT` (menu ESC via seed do `shortMenuLabels` do CPDD, com `debug.getupvalue` — **máx 10 tentativas depois desiste**), `_GLOSS` (conserta nome próprio EN dentro de frase PT), `sweep()` (deep-walk EN→PT), `pat_fix`/`pat_fallback`. `H._dev` = `_G.__hp._dev` setado pelo `Init.lua`.
- **Dev**: marcador `_tl_dump/.dev` → hot-reload + captura de faltas + `_menu_probe.txt`. `_tl_dump/run` → `do_dump` completo (trava o loading, só p/ dump navegado). `gamepatch.install(dump=False)` **sempre** apaga `_tl_dump/`.

### GOTCHAS que já custaram caro
- `File.LoadFile` devolve `""` (não `nil`) p/ arquivo inexistente.
- `os.time()`/`os.clock()` constantes no sandbox → cooldown por contador de execução (`H.runs`).
- `require("mods.X")` no bootstrap do CPDD só funciona se `cpdd_user_settings.lua` for lido — se rodar `gamepatch.install` com o **jogo aberto**, o bootstrap já leu o arquivo antigo e o deploy não tem efeito até relançar.
- `debug.getupvalue` em loop varrendo `LOMModLoader.Hooks` inteiro = **freeze** de usuários (01/09). Qualquer traversal de funções precisa de limite duro.
- Traduzir enum/estado (`shortMenuLabels` é seguro — só display; `visibleTextCache`/`visibleTextExactOverrides` do CPDD NÃO — quebra o CN→EN).

---

## 📢 NOTIFICAÇÃO DE PATCH DE TRADUÇÃO

`translations_index.json` (e o remoto) tem `games[].patch_notes[]` — lista de `{version, date, items[]}`. Ao abrir "Tradução de jogos" (ou ao instalar), o app compara com o último `patch_notes` visto (`config["seen_patch_notes"][game_id]`) e mostra o que mudou. Ver `game_translate.py` / `library.py`.

---

## 🚀 ENTREGA

- Branch de trabalho, PR → `main`. Depois do merge: `gh release create vX.Y.Z ... download/AMSTranslatorSetup.exe`.
- Mudança em `hotpatch.lua`/`Init.lua`/`pt/*.lua`: commitar nos **dois** repos (dev `luamod/` + `ams-translator-traducoes/lord-of-mysteries/pt/`) — o app baixa do segundo.
- Mudança de Python/spec/iss: rebuild do `.exe` + instalador + `cp` pro `download/`.
