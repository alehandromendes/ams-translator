# Tradutor de Legendas

**Traduza legendas e textos de jogos para português — ao vivo, sem tradução oficial e sem chave de API.**

Aplicativo de desktop para Windows. Nasceu para *Lord of Mysteries* (诡秘之主), mas
funciona com qualquer jogo. Duas frentes:

- **Captura ao vivo** — um atalho global (ou `Ctrl+V`) tira um print, faz OCR do texto,
  traduz e mostra numa galeria com a legenda **substituída no lugar**, no estilo do
  Google Tradutor.
- **Tradução de jogos** — baixa e instala pacotes de tradução para mods do jogo,
  direto de uma [biblioteca no GitHub][lib], sempre com **backup do original** e
  restauração em um clique.

---

## ⬇️ Download

### 👉 [**Baixar TradutorDeLegendasSetup.exe**](https://github.com/alehandromendes/tradutor-legendas/raw/main/download/TradutorDeLegendasSetup.exe)

Também disponível na pasta [`download/`](download/) do repositório e na página de
**[Releases][rel]**. Link fixo para a última versão:
`.../releases/latest/download/TradutorDeLegendasSetup.exe`

Assistente de instalação em PT-BR / EN, cria atalhos no menu Iniciar e na área de
trabalho. **Windows 10/11 (64 bits). Não precisa de Python.**

> O app solicita elevação (UAC) ao abrir — é necessário para os atalhos globais
> funcionarem por cima de jogos que rodam como administrador.

---

## Recursos

- OCR de chinês **offline** (RapidOCR / ONNX) — nada sai da máquina até a tradução
- Tradução **sem chave de API**, com _fallback_ entre provedores públicos
- Galeria paginada com miniaturas, navegação por teclado/atalho e auto-avanço inteligente
- Legenda **recomposta na imagem** por cima do texto original
- Glossário de nomes próprios (`glossary/*.csv`) aplicado antes de traduzir
- Painel reverso **PT → 中文** para digitar e traduzir
- Janela sem moldura, tema escuro, atalhos globais configuráveis (Win32 + hook)
- **Colar imagem** (`Ctrl+V`) para traduzir qualquer print

---

## Modo 1 — Captura ao vivo

1. **Definir região** — a tela congela; arraste sobre a faixa onde a legenda aparece.
   Uma faixa baixa e larga deixa o OCR quase instantâneo.
2. No jogo, a cada fala nova aperte o atalho:
   - **PgUp** — captura a região definida
   - **PgDn** — captura a tela inteira
   - **`Ctrl+V`** — traduz uma imagem da área de transferência
3. Navegue pela galeria com as **setas ← →**, pelos botões, pela filmstrip, ou pelos
   atalhos globais de navegação (configuráveis).
4. **Ver traduzido** alterna com o original. **Copiar** / **Salvar** exportam o resultado.

Todos os atalhos são reconfiguráveis em **Atalhos** (grave qualquer combinação).

---

## Modo 2 — Tradução de jogos

Botão **Tradução de jogos** na barra de ações:

1. O app lê o índice da [biblioteca de traduções][lib] no GitHub.
2. **Baixar** — traz os arquivos da tradução para `…/TradutorDeLegendas/traducoes/<jogo>/`.
3. O app **detecta a pasta do jogo** e confere se a estrutura bate com o esperado.
4. **Instalar** — copia os arquivos para o jogo, guardando o original antes.
5. **Restaurar original** desfaz a qualquer momento.

Suporte inicial: **Lord of Mysteries** — tradução em ponte **中文 → EN → PT-BR**. O jogo
é em chinês; o [CPDD English patch](https://github.com/Lani27/lord-of-mysteries-english-patch)
já faz 中文 → inglês, e este pacote traduz o inglês do patch → PT-BR (o inglês serve de
pivô: nomes já vêm anglicizados e a tradução sai melhor que CN→PT direto). Reinstale
após cada atualização do patch.

---

## Configuração — `overlay_config.json`

Criado no primeiro uso, ao lado do executável (ou em `%LOCALAPPDATA%\TradutorDeLegendas\`).

| chave | padrão | função |
|---|---|---|
| `hotkeys_region` / `hotkeys_fullscreen` | `["pgup"]` / `["pgdown"]` | atalhos de captura (região / tela inteira) |
| `nav_prev_hotkeys` / `nav_next_hotkeys` | `["left"]` / `["right"]` | navegar a galeria com o jogo em foco |
| `region` | `null` | faixa da legenda (definida pela interface) |
| `monitor` | `1` | monitor usado quando não há região |
| `source_lang` / `target_lang` | `zh-CN` / `pt` | par de idiomas |
| `min_ocr_score` | `0.5` | descarta OCR abaixo desse score |
| `hide_window_on_capture` | `true` | oculta a janela 0,1 s para não capturar a si mesma |
| `max_pages` | `10` | quantas capturas a galeria mantém |
| `auto_advance_gap_seconds` | `60` | intervalo mínimo para a galeria pular para a captura nova |
| `reverse_panel_visible` | `true` | mostra o painel PT → 中文 |

---

## Para desenvolvedores

### Rodar do código

```bash
git clone https://github.com/alehandromendes/tradutor-legendas
cd tradutor-legendas
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m overlay
```

### Gerar o executável e o instalador

```bash
build_exe.bat
#   -> dist/Tradutor de Legendas/   (~340 MB — PySide6 + onnxruntime + modelos OCR)

powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
#   -> installer/Output/TradutorDeLegendasSetup.exe
```

`build_installer.ps1` gera o `.exe` se necessário, instala o Inno Setup (winget/choco)
se faltar, e compila o assistente.

### Ferramentas de linha de comando

```bash
# Gera/atualiza a tradução do CPDD English patch (RuntimeTextGemini.lua + Init.lua):
# traduz o inglês do patch -> PT-BR, fechando a ponte 中文 -> EN -> PT-BR
python -m overlay.gamefill.patch_pt [--status | --restore | --no-init]

# Preenche as lacunas de um mod de localização PT da comunidade (formato .parts/*.lua)
python -m overlay.gamefill [--dry-run | --restore]
```

Ambos fazem backup do original e são reexecutáveis (retomam de onde pararam).

---

## Como funciona

```
atalho global (PgUp região / PgDn tela inteira)  ─ ou ─  Ctrl+V
  → captura (mss)
  → fila em thread de trabalho
      → OCR de chinês (RapidOCR / ONNX, offline)
      → junta os fragmentos de cada linha
      → tradução CN → PT (Google clients5 → gtx → MyMemory), sem chave
         + glossário de nomes próprios
      → recompõe a imagem por cima da legenda original
  → galeria: filmstrip + navegação + auto-avanço (buffer circular de 10)
```

A tradução de mods (`overlay/gamefill/`) trabalha sobre os arquivos `.lua` que o mod de
tradução do jogo já instalou, protegendo a marcação (`<InvHighlight>`, `<Mark id=…>`,
`%s`, quebras de linha) e fixando termos de jogo ambíguos via `game_terms.csv`
(`gear` → equipamento, `dungeon` → masmorra, `Beyonder`, `Sequência`…). Só escreve na
pasta do usuário do jogo (`Saved/Mods/`), fora da verificação de integridade dos `.pak`.

---

## Limitações

- **Fullscreen exclusivo** dá tela preta na captura — use modo janela / *borderless*.
  `Ctrl+V` funciona sempre.
- **Atalhos globais** registram por Win32 `RegisterHotKey` + hook. Se um jogo elevado
  ignorar, o app roda elevado por padrão; o indicador no rodapé mostra o estado.
- Teclas em uso por outro programa (GeForce Experience, OBS…) são avisadas — troque em
  **Atalhos**.
- Tradução por endpoints públicos: podem limitar por IP (`429`); o app cai para o
  próximo e nada quebra. Traduções ficam em cache.
- A tradução de mods é **automática** — o original fica sempre salvo para restaurar.

---

## Stack

Python · PySide6 · mss · RapidOCR (onnxruntime) · Pillow · requests · keyboard · PyInstaller · Inno Setup

---

## Sobre as traduções

Tudo aqui — legendas capturadas ao vivo e pacotes da
[biblioteca de traduções][lib] — é traduzido por **inteligência artificial**
(tradução automática, sem chave de API e sem revisão humana linha a linha), com
**estratégias de desambiguação voltadas a jogos**:

- **Dicionário de termos ambíguos** (`overlay/gamefill/game_terms.csv`) — fixa o
  sentido de jogo de palavras com duas leituras: *gear* → equipamento (não
  "engrenagem"), *cast* → conjurar, *dungeon* → masmorra, *cooldown* → recarga,
  *raid* → raide, *party mode* → modo em grupo…
- **Termos do universo preservados** — *Beyonder*, *Sequência*, *Caminho*,
  *Vigia Noturno*, *Marionete*, mais o glossário de nomes próprios
  (`glossary/*.csv`), aplicado **antes** de traduzir.
- **Marcação protegida** — tags (`<InvHighlight>`, `<Mark id=…>`), variáveis
  (`%s`, `{0}`) e quebras de linha passam intactas pela tradução.

É tradução de máquina e pode escorregar. Nas traduções de jogos, o **arquivo
original é salvo antes de instalar** e restaurado em um clique.

## Licença

[MIT](LICENSE) © 2026 Alehandro Mendes. Este projeto não redistribui conteúdo dos jogos.

[lib]: https://github.com/alehandromendes/tradutor-legendas-traducoes
[rel]: https://github.com/alehandromendes/tradutor-legendas/releases/latest
