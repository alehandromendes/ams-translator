# Tradutor de Legendas

App de desktop (Windows, Python + PySide6) que traduz **legendas de jogos ao vivo** —
sem tradução oficial, sem chave de API. Feito em cima de *Lord of Mysteries* (诡秘之主),
mas serve pra qualquer jogo.

Dois modos:

1. **Captura ao vivo** — atalho global (ou `Ctrl+V`) → OCR do chinês → tradução PT →
   galeria com a legenda **substituída no lugar**, estilo Google Tradutor.
2. **Tradução de jogos** — baixa e instala traduções de mods do jogo (da biblioteca
   [`tradutor-legendas-traducoes`](https://github.com/alehandromendes/tradutor-legendas-traducoes)),
   com backup do original e um clique pra restaurar.

> Licença MIT. Não redistribui conteúdo do jogo — as traduções são geradas por
> tradução automática sobre os arquivos que o próprio usuário já tem instalados.

## Instalação

- **Usuário:** baixe o instalador em *Releases* (`TradutorDeLegendasSetup.exe`) e siga o
  assistente. Ou baixe a pasta `Tradutor de Legendas/` do .zip e rode o `.exe`.
- **Do código:** veja *Setup* abaixo.

---

## Como funciona (captura ao vivo)

```
atalho global (F9 região / F8 tela inteira)  ─ ou ─  Ctrl+V (imagem colada)
  → captura via mss
  → fila de um worker em thread separada
      → OCR chinês (RapidOCR / ONNX, offline)
      → junta os fragmentos da mesma linha num texto só
      → tradução CN→PT sem chave (Google clients5 → gtx → MyMemory)
         + pré-substituição de nomes pelo glossary/*.csv
      → recompõe a imagem cobrindo a legenda original e escrevendo o PT no lugar
  → galeria paginada: filmstrip de miniaturas + ◀ Anterior / Próxima ▶ (setas ← →),
    ordem cronológica, mantém só as últimas 10 (buffer circular)
```

---

## Setup

```bash
git clone https://github.com/alehandromendes/tradutor-legendas
cd tradutor-legendas
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Rodar

```bash
python -m overlay          # ou: python run_overlay.py
```

Ou **duplo-clique em `Tradutor de Legendas.bat`**.

1. **Definir região** → a tela congela (visível, levemente escurecida, com linhas-guia); arraste sobre a faixa da legenda. **Dica:** uma faixa baixa e larga (proporção > 8:1) faz o OCR pular a etapa de detecção e fica quase instantâneo. Salvo em `overlay_config.json`.
2. **Atalhos** → 4 grupos, todos globais (funcionam com o jogo em foco):
   - **Capturar região** (padrão F9) e **Capturar tela inteira** (padrão F8)
   - **Página anterior** / **Próxima página** — configure aqui p/ navegar as traduções **sem sair do jogo** (as setas ← → do teclado só funcionam com a janela do app em foco).
   Grave qualquer combinação; vários por grupo; aplica na hora. Se o atalho de região for apertado sem região definida, o app abre a seleção primeiro e captura em seguida.
3. No jogo, a cada fala nova, aperte o atalho — **ou** copie um print e tecle **Ctrl+V** na janela.
4. Navegue pelas **setas** nas laterais do visor, pela **filmstrip** à esquerda, pelos botões **Anterior / Próxima** ou pelas **setas do teclado**. Checkbox **Ver traduzido** alterna com o original.
   - **Auto-avanço inteligente:** se a captura anterior foi há **menos de `auto_advance_gap_seconds` (60 s)**, a galeria **não pula** pra nova (o botão *Próxima (N)* mostra quantas esperam). Se passou ≥ 60 s, vai direto pra nova.
5. **Copiar** (CN⭾PT) · **Salvar** (PNG em `data/overlay_shots/`).
6. **Painel PT → 中文** (direita, liga/desliga na toolbar): digite em português → tradução em chinês simplificado (Ctrl+Enter, botão, ou 0,8 s após parar de digitar) + **Copiar 中文**.

## Configuração — `overlay_config.json` (criado no 1º uso)

| chave | padrão | o que faz |
|-------|--------|-----------|
| `hotkeys_region` / `hotkeys_fullscreen` | `["f9"]` / `["f8"]` | atalhos globais: captura da região pré-config / da tela inteira |
| `nav_prev_hotkeys` / `nav_next_hotkeys` | `[]` | atalhos globais p/ navegar a galeria com o jogo em foco (ex.: `["page up"]` / `["page down"]`) |
| `region` | `null` | região da legenda (setada pela UI) |
| `monitor` | `1` | monitor usado quando não há região |
| `source_lang` / `target_lang` | `zh-CN` / `pt` | par de idiomas |
| `min_ocr_score` | `0.5` | descarta OCR abaixo desse score |
| `font_path` | Segoe UI Semibold | fonte do texto traduzido |
| `hide_window_on_capture` | `true` | some com a janela 0,1 s pra não capturar a si mesma |
| `max_pages` | `10` | quantas capturas a galeria mantém |
| `auto_advance_gap_seconds` | `60` | intervalo mínimo entre capturas p/ a galeria pular pra nova automaticamente |
| `reverse_panel_visible` | `true` | mostra o painel PT → 中文 |
| `reverse_source` / `reverse_target` | `pt` / `zh-CN` | direção do painel de digitação |

## Glossário — `glossary/*.csv`

Termos chineses conhecidos são trocados pela forma PT-BR **antes** de ir pro tradutor,
então nomes próprios saem certos. Formato: `cn,en,pt_br,category,notes`.

## Gerar o .exe e o instalador

```bash
build_exe.bat        # -> dist/Tradutor de Legendas/  (~340 MB, PySide6 + onnxruntime + modelos OCR)

powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
#   -> installer/Output/TradutorDeLegendasSetup.exe  (assistente Inno Setup)
```

`build_installer.ps1` gera o `.exe` se preciso, instala o Inno Setup (winget/choco) se
faltar, e compila o assistente. Distribua **só o `TradutorDeLegendasSetup.exe`** — ou a
pasta `dist/Tradutor de Legendas/` inteira. Não precisa de Python na máquina destino.

- `overlay_config.json`, `data/cache/` e `data/overlay_shots/` ficam **ao lado do .exe**.
- Glossário vai embutido; pra editar depois, ponha uma pasta `glossary/` ao lado do .exe (tem prioridade).

## Traduzir o jogo para PT (botão "Traduzir jogo")

Se o jogo usa um **mod de tradução para inglês** (ex.: CPDD English patch de *Lord of
Mysteries*), o botão **Traduzir jogo** na barra de ações traduz os textos do mod de
**EN → PT-BR** com a mesma API, direto nos arquivos do mod:

- Alvo: `C7/Saved/Mods/lua/mods/cpdd_runtime_fixes/RuntimeTextGemini.lua` (mapa
  `中文 → English` que o patch usa pra todo texto visível — 126 mil linhas).
- **Salva o original** em `gamefill/backup/` antes de tocar em nada; botão
  **Restaurar original** volta byte-idêntico.
- Protege markup (`<InvHighlight>`, `<Mark id=…>`, `%s`, quebras de linha) e fixa
  termos de jogo ambíguos (`overlay/gamefill/game_terms.csv`: `gear`→equipamento,
  `Beyonder`, `Sequência`, `dungeon`→masmorra…).
- **Leva horas** (~7,9 M caracteres). Roda em thread, mostra progresso, dá pra
  **Parar** e continuar depois (cache em `gamefill/patch_pt_cache.json`).
- Reinicie o jogo pra ver. Rode de novo depois de cada atualização do patch.

CLI equivalente: `python -m overlay.gamefill.patch_pt [--status|--restore]`

## Preencher o mod de tradução do jogo (`overlay.gamefill`)

> Para o caso do mod de localização **PT** da comunidade (formato `.parts/*.lua`).
> Se você usa o **English patch**, veja a seção acima.

Lord of Mysteries (诡秘之主) já roda com um **mod de localização da comunidade**
(`<jogo>/C7/Saved/Mods/localization/`) que traduz ~98% dos textos. As ~500 linhas de
**diálogo** que sobraram em chinês podem ser preenchidas com o mesmo motor + glossário:

```bash
python -m overlay.gamefill --dry-run      # prévia, não grava nada
python -m overlay.gamefill                # aplica (FECHE O JOGO ANTES)
python -m overlay.gamefill --restore      # desfaz
```

Ou **duplo-clique em `Preencher traducao do jogo.bat`**.

- Acha as strings dos módulos de conversa com CJK residual, resolve `{{先生|女士}}` →
  `{{senhor|senhora}}`, aplica o glossário (nomes) e traduz o resto.
- Grava um fragmento `.parts/NNNN.lua` de **overlay** que o próprio mod carrega por cima
  e faz `+1` no `__parts` do índice (índice original salvo em `gamefill/backup/`).
- Toda linha preenchida ganha o prefixo **`» `** (`--no-mark` desliga) pra você revisar
  no jogo; as mais incertas ficam **`»? `**. Relatório completo em `gamefill/report.csv`.
- Re-executável: `state.json` evita re-traduzir o que já foi feito. Rode de novo depois
  de cada atualização do mod da comunidade (ela sobrescreve nosso overlay).
- Só mexe em `C7/Saved/Mods/` (pasta do usuário, fora da verificação dos `.pak`) — mesmo
  mecanismo do mod que já está instalado.

## Limitações

- **Jogo em modo janela / "borderless windowed"** — fullscreen exclusivo dá tela preta na captura. `Ctrl+V` funciona sempre.
- **Atalho global:** o app registra por dois caminhos (Win32 `RegisterHotKey` + hook). Se não pegar por cima de um jogo que roda como administrador, use o botão **Reabrir como admin**.
- Se a tecla escolhida já estiver em uso (GeForce Experience, OBS, ShareX usam F-keys), o app avisa — troque em **Atalhos**. O indicador no cabeçalho mostra ativo / sem admin / falhou.
- Os botões da toolbar e o **Ctrl+V** funcionam sempre (com a janela em foco).
- Tradução usa endpoints públicos sem chave (clients5 → MyMemory → Lingva → gtx) — podem limitar por IP (`429`); cai pro próximo. Se **todos** falharem, o app mostra o motivo na barra de status e o botão **Retraduzir** fica em destaque (nada é gravado no cache, então o retry funciona). Cache em `data/cache/overlay_tm.json`.
- Velocidade típica por captura: OCR ~0,2–0,4 s + tradução ~0,3–1,8 s (latência de rede). A barra de status mostra os dois tempos. Legenda repetida = cache, instantâneo.

## Stack

Python · PySide6 · mss · RapidOCR (onnxruntime) · Pillow · deep-translator/requests · keyboard · PyInstaller
