-- v19: v18 + hook GLOBAL de SetText/SetName em qualquer classe de widget de texto
local T = _G.__tl
if not T then return "sem __tl" end
local en2pt, rep = T.en2pt, T.report
_G.__hp = _G.__hp or {}
local H = _G.__hp
H.resweep_on = true

local nmod = 0
for _ in pairs(package.loaded) do nmod = nmod + 1 end

-- ===== PASSE DE LOGIN: roda TODA vez ate estabilizar. Varre package.loaded
-- INTEIRO atras dos textos exatos da tela de login/selecao de personagem. =====
do
  local LOGIN_OVR = {
    ["Select Character"] = "Selecionar Personagem", ["Character Select"] = "Selecionar Personagem",
    ["Enter World"] = "Entre no mundo dos Beyounders",
    ["Enter the World"] = "Entre no mundo dos Beyounders",
    ["Enter the Extraordinary World"] = "Entre no mundo dos Beyounders",
    ["Enter Extraordinary World"] = "Entre no mundo dos Beyounders",
    ["\232\191\155\229\133\165\233\157\158\229\135\161\228\184\150\231\149\140"] = "Entre no mundo dos Beyounders",
    ["Create Character"] = "Criar Personagem", ["Delete Character"] = "Excluir Personagem",
    ["Create Role"] = "Criar Personagem", ["Delete Role"] = "Excluir Personagem",
    ["Connect to Server"] = "Conectando ao servidor", ["Connecting"] = "Conectando",
    ["Connecting..."] = "Conectando...", ["Reconnecting"] = "Reconectando",
    ["Reconnecting..."] = "Reconectando...", ["Loading"] = "Carregando",
    ["Loading..."] = "Carregando...", ["Verifying resource files"] = "Verificando arquivos",
    ["Music"] = "Musica", ["Repair"] = "Reparar", ["Feedback"] = "Feedback",
    ["Login"] = "Entrar", ["Log in"] = "Entrar", ["Exit"] = "Sair",
    ["Announcement"] = "Aviso", ["Server"] = "Servidor", ["Server List"] = "Lista de Servidores",
    ["Start Game"] = "Iniciar Jogo", ["Confirm"] = "Confirmar", ["Cancel"] = "Cancelar",
  }
  local hit = _G.__login_hit or 0
  local seen0 = {}
  local function lw(t, d)
    if type(t) ~= "table" or seen0[t] or d > 8 then return end
    seen0[t] = true
    pcall(function()
      for k, v in pairs(t) do
        local ks = tostring(k)
        if ks ~= "class" and ks:sub(1, 2) ~= "__" then
          if type(v) == "string" then
            local p = LOGIN_OVR[v]
            if p and p ~= v then t[k] = p; hit = hit + 1 end
          elseif type(v) == "table" then lw(v, d + 1) end
        end
      end
    end)
  end
  for _, mod in pairs(package.loaded) do
    if type(mod) == "table" then pcall(lw, mod, 0) end
  end
  if type(_G.Game) == "table" then pcall(lw, _G.Game, 0) end
  _G.__login_hit = hit
  rep["hp_login"] = "login hits=" .. hit .. " (nmod=" .. nmod .. ")"
end

if nmod < 180 then rep["hp"] = "carregando (" .. nmod .. ")"; return "wait" end

local DISPLAY_KEY = { Name=1,Title=1,Desc=1,Description=1,Text=1,Content=1,Tip=1,
  Tips=1,SubName=1,ShortName=1,Summary=1,Detail=1,Details=1,Label=1,Comment=1,
  Target=1,TargetDesc=1,RewardDesc=1,UIName=1,DisplayName=1,TabName=1,GroupName=1,
  BtnName=1,DescStr=1,NameStr=1,TitleStr=1,ConditionDesc=1,Word=1,TextInfo=1,
  BubbleText=1,LevelName=1,LevelDesc=1,Nickname=1,pName=1,pDesc=1,
  -- dropdown / selectbox: valor exibido
  CurText=1,SelectedText=1,curValue=1,ShowText=1,DisplayText=1,OptionText=1,
  CurrentText=1,SelectText=1,ValueText=1,curText=1,selectedName=1 }
local SKIP = { class=1,__index=1,__supers=1,receiver=1,sender=1,__hp=1,package=1,
  loaded=1,preload=1,_G=1,["_ENV"]=1,EventDefine=1,eventsV2=1,metatable=1,
  StateName=1,State=1,Type=1,Tag=1,Id=1,ID=1,Key=1,Event=1,EventName=1,
  Action=1,Cmd=1,Command=1,Anim=1,Animation=1,Bone=1,Socket=1,Path=1,
  Icon=1,Sound=1,Audio=1,Effect=1,Prefab=1,Asset=1,Res=1,Url=1 }

-- overrides curados de labels curtos (o MT erra ou o sweep nao pega)
local OVR = {
  ["Main Quest"] = "Missão Principal", ["Side Quest"] = "Missão Secundária",
  ["Original Work"] = "Obra Original", ["Settings"] = "Configurações",
  ["Basic"] = "Básico", ["Audio"] = "Áudio", ["Frame"] = "Imagem",
  ["Combat"] = "Combate", ["Keybinds"] = "Teclas", ["Camera"] = "Câmera",
  ["Social"] = "Social", ["Account"] = "Conta", ["Vault"] = "Cofre",
  ["Store"] = "Loja", ["Library"] = "Biblioteca", ["Plaza"] = "Praça",
  ["Level"] = "Nível", ["Exit Game"] = "Sair do Jogo", ["Scene Marker"] = "Marcador de Cena",
  ["Teammate Marker"] = "Marcador de Aliado", ["Rally"] = "Reunir",
  ["Confirm exiting the game?"] = "Confirmar saída do jogo?",
  ["Recently Completed"] = "Concluídas Recentemente", ["Plot"] = "Enredo",
  ["Personal"] = "Pessoal", ["Fashion Level"] = "Nível de Moda",
  ["Achievement Points"] = "Pontos de Conquista", ["Player"] = "Jogador",
  ["Pathway"] = "Caminho", ["Club"] = "Clube", ["Competition"] = "Competição",
  ["Dungeon"] = "Masmorra", ["Family"] = "Família", ["Castle"] = "Castelo",
  ["Cult"] = "Culto", ["Unranked"] = "Sem classificação", ["All Pathways"] = "Todos os Caminhos",
  ["Spectator"] = "Espectador", ["Bard"] = "Bardo", ["Seer"] = "Vidente",
  ["Warrior"] = "Guerreiro", ["Apprentice"] = "Aprendiz", ["Mystery Pryer"] = "Investigador de Mistérios",
  ["World Adventure"] = "Aventura Mundial", ["TRPG"] = "TRPG", ["Leisure"] = "Lazer",
  ["Fun Combat"] = "Combate Divertido", ["Travel Tracks"] = "Rotas de Viagem",
  ["Gameplay Entry"] = "Entrada de Jogo", ["Rank Quest"] = "Missão de Rank",
  ["Daily"] = "Diário", ["Team Instance"] = "Instância em Grupo",
  ["Store Lv"] = "Loja Nv", ["marionette"] = "Fantoches", ["Marionette"] = "Fantoches",
  ["Send"] = "Enviar", ["Chat"] = "Bate-papo", ["Friends"] = "Amigos",
  ["Voice Room"] = "Sala de Voz", ["Mail"] = "Correio", ["Steps:"] = "Passos:",
  ["Spirit Vision"] = "Visão Espiritual", ["Requiem"] = "Réquiem", ["Sanity"] = "Sanidade",
  ["Requiem button"] = "botão de Réquiem", ["Need help?"] = "Precisa de ajuda?",
  ["Related Notes:"] = "Notas Relacionadas:", ["Sealed Artifact"] = "Artefato Selado",
  ["Beyonder"] = "Beyonder", ["点击输入"] = "Clique para digitar",
  ["Visual Guide:"] = "Guia Visual:",
  ["Aumentar a favorabilidade"] = "Aumentar vinculo",
  ["Attack"] = "Ataque",
  ["Recommended Builds"] = "Builds Recomendadas", ["My Builds"] = "Minhas Builds",
  ["Training Dummy"] = "Boneco de Treino", ["One-Click Assist"] = "Auxilio Rapido",
  ["One-Click Upgrade"] = "Melhoria Rapida", ["Equip Skill"] = "Equipar", ["Equipar Habilidade"] = "Equipar",
  ["Normal Skill"] = "Habilidade Comum", ["Special Skill"] = "Habilidade Especial",
  ["Roleplay Skill"] = "Habilidade de Interpretacao", ["Finisher Skill"] = "Finalizadora",
  ["Conquest"] = "Conquista", ["Factions"] = "Faccoes", ["Faction"] = "Faccao",
  ["Antigonus Notebook"] = "Caderno Antigonus", ["Caderno Antigono"] = "Caderno Antigonus",
  ["Caderno Antigonus"] = "Caderno Antigonus", ["Defense"] = "Defesa", ["Health"] = "Vida", ["HP"] = "Vida",
  ["Chaos"] = "Caos", ["Enlightenment"] = "Iluminacao", ["Pathfinding"] = "Exploracao",
  ["Speculation"] = "Especulacao", ["Interpretation"] = "Interpretacao",
  ["Historical Research"] = "Pesquisa Historica", ["Final Damage Bonus"] = "Bonus de Dano Final",
  ["Final Damage Block"] = "Bloco de Dano Final", ["Final Damage"] = "Dano Final", ["Increase Favorability"] = "Aumentar vinculo",
  ["Increase favorability"] = "Aumentar vinculo", ["Favorability"] = "Vinculo",
  ["Nivel de conexao aumentado"] = "Nivel de vinculo aumentado",
  -- menu de estilo/aparencia
  ["Close"] = "Desativar", ["Open"] = "Ativar", ["On"] = "Sim", ["Off"] = "Não",
  ["Enable"] = "Ativar", ["Disable"] = "Desativar", ["Enabled"] = "Ativado", ["Disabled"] = "Desativado",
  ["Low"] = "Baixo", ["Medium"] = "Médio", ["High"] = "Alto", ["Ultra"] = "Ultra",
  ["Ultra High"] = "Ultra", ["Cinematic"] = "Cinemático", ["Customize"] = "Personalizar",
  ["Custom"] = "Personalizado", ["Auto"] = "Automático", ["Manual"] = "Manual", ["Default"] = "Padrão",
  ["Near"] = "Perto", ["Far"] = "Longe", ["None"] = "Nenhum", ["Balanced"] = "Equilibrado",
  ["Native"] = "Nativo", ["Quality"] = "Qualidade", ["Performance"] = "Desempenho",
  ["Windowed"] = "Janela", ["Fullscreen"] = "Tela cheia", ["Borderless"] = "Sem bordas",
  ["Frame Generation"] = "Geração de quadros", ["Upscaling Mode"] = "Modo de escala",
  ["Resolution"] = "Resolução", ["Field of View"] = "Campo de visão",
  ["Restore Defaults"] = "Restaurar Padrões", ["Switch character"] = "Trocar Personagem",
  ["Ray Tracing"] = "Ray Tracing", ["Graphics Settings"] = "Configurações Gráficas",
  ["Overview"] = "Visão Geral", ["Peripheral"] = "Acessórios", ["Weapon"] = "Arma",
  ["Vehicle"] = "Veículo", ["Body Aura"] = "Aura Corporal", ["Footprints"] = "Pegadas",
  ["Idle"] = "Parado", ["Action"] = "Acao",
  ["Head"] = "Cabeça", ["Hands"] = "Mãos", ["Expositor"] = "Expositor",
  -- HUD/party
  ["Locked Childhood"] = "Infância Trancada",
  ["Distract the parents"] = "Distrair os pais", ["Return to Plane"] = "Voltar ao Plano",
  ["View Jenny's manuscript"] = "Ver o manuscrito da Jenny",
  ["Go to"] = "Ir para", ["Track Quest"] = "Rastrear Missão",
  ["Cancel Tracking"] = "Cancelar Rastreamento", ["Quest Target"] = "Alvo da Missão",
  ["Quest reward"] = "Recompensa da Missão", ["Quest Reward"] = "Recompensa da Missão",
  ["All"] = "Todas", ["System"] = "Sistema", ["Era"] = "Era", ["Roaming"] = "Roaming",
  -- correcoes pedidas pelo usuario
  ["Condado Branco Puro"] = "Cavalo Branco de Napoleão",
  ["Monarca: Chama"] = "Monarca das Chamas",
  ["Monarca: Abismo"] = "Monarca do Abismo",
  ["Monarca: Resplendor Sagrado"] = "Monarca do Resplendor",
  ["Monarca: Cristal de Gelo"] = "Monarca do Gelo",
  ["Monarch: Flame"] = "Monarca das Chamas",
  ["Monarch: Abyss"] = "Monarca do Abismo",
  ["Monarch: Sacred Radiance"] = "Monarca do Resplendor",
  ["Monarch: Ice Crystal"] = "Monarca do Gelo",
  ["Acceleration."] = "Aceleração.", ["Acceleration"] = "Aceleração",
  ["Pure White County"] = "Cavalo Branco de Napoleão",
  -- aba de eventos
  ["Event"] = "Eventos", ["Loen Fashion"] = "Moda de Loen",
  ["Cumulative"] = "Acumulado", ["Cumulative1 Day"] = "Acumulado: 1 Dia",
  ["Final Reward"] = "Recompensa Final", ["First Purchase"] = "Primeira Compra",
  ["Hidden Space"] = "Espaço Oculto", ["Season Guide"] = "Guia da Temporada",
  ["Day 1"]="Dia 1",["Day 2"]="Dia 2",["Day 3"]="Dia 3",["Day 4"]="Dia 4",
  ["Day 5"]="Dia 5",["Day 6"]="Dia 6",["Day 7"]="Dia 7",["Day 8"]="Dia 8",
  ["Day 9"]="Dia 9",["Day 10"]="Dia 10",["Day 11"]="Dia 11",["Day 12"]="Dia 12",
  ["1 Day"]="1 Dia",["2 Days"]="2 Dias",["3 Days"]="3 Dias",["4 Days"]="4 Dias",
  ["5 Days"]="5 Dias",["6 Days"]="6 Dias",["7 Days"]="7 Dias",["8 Days"]="8 Dias",
  ["9 Days"]="9 Dias",["10 Days"]="10 Dias",
  -- lote menu Divino / avanço
  ["Advancement"] = "Divino", ["Sustain War with War"] = "Combate entre Jogadores",
  ["Sustentar a guerra com a guerra"] = "PvP",
  ["Pathway Conversion"] = "Mudar Caminho", ["Caminho Conversão"] = "Mudar Caminho",
  ["Caminho Conversao"] = "Mudar Caminho",
  ["Pathway Description"] = "Descrição", ["Caminho Descrição"] = "Descrição",
  ["Caminho Descricao"] = "Descrição", ["Pathway Description"] = "Descrição",
  ["Acting Level Reached"] = "Nível de atuação", ["Nível de atuação alcançada"] = "Nível de atuação",
  ["Nivel de atuacao alcancada"] = "Nível de atuação",
  ["Collected all materials"] = "Materiais coletados",
  ["Coletou todos os materiais"] = "Materiais coletados",
  ["Final Hunt"] = "Caçada Final", ["Trickmaster"] = "Mestre dos Truques",
  ["Viscount Tier 4"] = "Visconde Nível 4", ["Viscount Tier"] = "Visconde Nível",
  ["Baron Tier"] = "Barão Nível", ["Knight Tier"] = "Cavaleiro Nível",
  ["Count Tier"] = "Conde Nível", ["Marquis Tier"] = "Marquês Nível",
  ["Duke Tier"] = "Duque Nível",
  ["Poção do Aprendiz"] = "Digestão do Aprendiz",
  ["Poção do Espectador"] = "Digestão do Espectador",
  ["Poção do Bardo"] = "Digestão do Bardo",
  ["Poção do Vidente"] = "Digestão do Vidente",
  ["Poção do Guerreiro"] = "Digestão do Guerreiro",
  ["Apprentice Potion total"] = "Digestão do Aprendiz",
  ["Progress Reward"] = "Recompensa de progresso",
  ["Advance Reward"] = "Recompensa de avanço",
  ["Advancement Conditions"] = "Condições de Avanço",
  ["Advancement Changes"] = "Mudanças de Avanço",
  ["Sequence Quest"] = "Missão de Sequência", ["Sequência Missão"] = "Missão de Sequência",
  ["Use"] = "Usar", ["Held:"] = "Possui:", ["Held"] = "Possui", ["Inventory"] = "Inventário",
  ["Exchange"] = "Trocar", ["Limited time"] = "Tempo limitado", ["Ranked Ladder"] = "Escada Rankeada",
  ["Refund Store"] = "Loja de Reembolsos", ["Supplement Store"] = "Loja Complementar",
  ["Acquisition Method"] = "Método de Aquisição", ["Quantity available"] = "Quantidade disponível",
  ["Lowest price"] = "Menor preço",
  -- loja
  ["Shop"] = "Loja", ["Follow"] = "Seguir", ["Appearance"] = "Aparência",
  ["Equipment"] = "Equipamento", ["Materials"] = "Materiais",
  ["Beyonder material"] = "Material Beyonder", ["Beyonder Material"] = "Material Beyonder",
  ["My Listings"] = "Meus Anúncios", ["Purchase"] = "Comprar", ["Holding"] = "Possui",
  ["Holding 63"] = "Possui 63", ["From"] = "Custa", ["No price set"] = "Sem preço",
  ["nenhum preço definido"] = "Sem preço", ["Nenhum preço definido"] = "Sem preço",
  ["No Price Set"] = "Sem preço", ["输入搜索内容"] = "Buscar",
  ["Ten Thousand"] = "", ["Total cost:"] = "Custo total:", ["Quantity"] = "Quantidade",
  ["Recommended"] = "Recomendado", ["Monthly Card"] = "Cartão Mensal", ["Warehouse"] = "Armazém",
  ["Consignment"] = "Consignação", ["Auction"] = "Leilão",
  -- galeria de trajes / aparencia plaza
  ["Praça da Aparência"] = "Galeria de Trajes", ["Praca da Aparencia"] = "Galeria de Trajes",
  ["Appearance Plaza"] = "Galeria de Trajes", ["Appearance Square"] = "Galeria de Trajes",
  ["Popular"] = "Populares", ["Face"] = "Rosto", ["Outfit"] = "Traje",
  ["Dyeing"] = "Tingimento", ["Hairstyle"] = "Penteado", ["Take Photo"] = "Tirar Foto",
  ["Recommend"] = "Recomendados", ["Author"] = "Autor", ["Mine"] = "Meu",
  ["Go to Publish"] = "Ir para Publicar", ["Publish"] = "Publicar",
  ["Vendável"] = "Negociável", ["Vendavel"] = "Negociável",
  ["Sellable"] = "Negociável", ["Tradable"] = "Negociável",
  ["Can be sold"] = "Negociável", ["Can be traded"] = "Negociável",
  ["Drop"] = "Descer", ["Drop."] = "Descer.",
  ["Período de Validade"] = "Item expira em:", ["Periodo de Validade"] = "Item expira em:",
  ["Validity Period"] = "Item expira em:", ["Valid Period"] = "Item expira em:",
  ["Discard"] = "Descartar", ["Support to earn points"] = "Suporte para ganhar pontos",
  -- lote 31/08
  ["Enter the Extraordinary World"] = "Entre no mundo dos Beyounders",
  ["Enter Extraordinary World"] = "Entre no mundo dos Beyounders",
  ["Entre no mundo extraordinário"] = "Entre no mundo dos Beyounders",
  ["Entre no mundo extraordinario"] = "Entrar no mundo dos Beyounders",
  ["Enter World"] = "Entre no mundo dos Beyounders",
  ["Entra Blackhorn"] = "Entrar em Blackhorn", ["Enter Blackhorn"] = "Entrar em Blackhorn",
  ["Enter Blackthorn"] = "Entrar em Blackthorn", ["Entra Blackthorn"] = "Entrar em Blackthorn",
  ["Fritar"] = "Frye", ["Fry"] = "Frye",
  ["Picareta mágica afiada"] = "Machado mágico afiado",
  ["Picareta magica afiada"] = "Machado magico afiado",
  ["Sharp Magic Pickaxe"] = "Machado Mágico Afiado", ["Sharp Magical Pickaxe"] = "Machado Mágico Afiado",
  ["Reconnecting"] = "Reconectando", ["Reconecting"] = "Reconectando",
  ["Reconnecting..."] = "Reconectando...",
}

-- transforms por padrao (duracao "38Day20Hour" -> "38 dias 20 horas", etc)
local function pat_fix(v)
  -- prefixos compostos
  local rest = v:match("^Vend[áa]vel:%s*(.+)$")
  if rest then return "Negociável: " .. rest end
  rest = v:match("^Sellable:%s*(.+)$")
  if rest then return "Negociável: " .. rest end
  rest = v:match("^Held:%s*(.+)$")
  if rest then return "Possui: " .. rest end
  rest = v:match("^Holding:?%s*(%d.+)$")
  if rest then return "Possui: " .. rest end
  local d, h = v:match("^(%d+)%s*Days?(%d+)%s*Hours?$")
  if d then return d .. " dias " .. h .. " horas" end
  local d2 = v:match("^(%d+)%s*Days?$"); if d2 then return d2 .. " dias" end
  local h2 = v:match("^(%d+)%s*Hours?$"); if h2 then return h2 .. " horas" end
  local m2 = v:match("^(%d+)%s*Min$"); if m2 then return m2 .. " min" end
  local dm, hm, mm = v:match("^(%d+)Day(%d+)Hour(%d+)Min")
  if dm then return dm .. " dias " .. hm .. "h " .. mm .. "min" end
  return nil
end

-- tira acentos (a fonte do jogo nao renderiza á/ã/ç em algumas cutscenes)
local _ACC = {
  ["\195\161"]="a",["\195\160"]="a",["\195\162"]="a",["\195\163"]="a",["\195\164"]="a",
  ["\195\169"]="e",["\195\168"]="e",["\195\170"]="e",
  ["\195\173"]="i",["\195\172"]="i",["\195\174"]="i",
  ["\195\179"]="o",["\195\178"]="o",["\195\180"]="o",["\195\181"]="o",
  ["\195\186"]="u",["\195\185"]="u",["\195\187"]="u",["\195\188"]="u",
  ["\195\167"]="c",["\195\177"]="n",
  ["\195\129"]="A",["\195\128"]="A",["\195\130"]="A",["\195\131"]="A",
  ["\195\137"]="E",["\195\138"]="E",["\195\141"]="I",
  ["\195\147"]="O",["\195\148"]="O",["\195\149"]="O",
  ["\195\154"]="U",["\195\135"]="C",["\195\145"]="N",
}
local function strip_accents(s)
  return (s:gsub("\195[\128-\191]", _ACC))
end

local function tl_one(v)
  if type(v) ~= "string" or #v < 2 or #v > 4000 then return v end
  if OVR[v] then return strip_accents(OVR[v]) end
  local pf = pat_fix(v); if pf then return strip_accents(pf) end
  if v:find("[\228-\233]") or v:find("^[/%.#@<]") or v:find("^%u[%u_%d]+$") then return v end
  local p = en2pt(v)
  local ml = (#v < 20) and (#v * 0.6) or (#v * 0.35)
  if p and p ~= v and #p >= math.max(3, ml) then return strip_accents(p) end
  return v
end

local function ok_string(k, v)
  if OVR[v] then return true end
  local ks = type(k) == "string" and k or ""
  if SKIP[ks] or #v < 2 or #v > 4000 or not v:find("%a") then return false end
  if v:find("[\228-\233]") or v:find("^[/%.#@<]") or v:find("^%u[%u_%d]+$") then return false end
  if (v:find(" ") and #v >= 12) or DISPLAY_KEY[ks] then return true end
  return false
end
-- ===== SCAN: acumula strings EN nao-traduzidas p/ o proximo build =====
_G.__scan = _G.__scan or {}        -- { en_string = true }
_G.__scan_n = _G.__scan_n or 0
_G.__scan_dirty = _G.__scan_dirty or false
-- palavras que so aparecem em INGLES (p/ nao capturar PT ja traduzido)
local _EN_W = { [" the "]=1, [" of "]=1, [" to "]=1, [" and "]=1, [" you "]=1,
  [" your "]=1, [" is "]=1, [" are "]=1, [" will "]=1, [" can "]=1, [" for "]=1,
  [" with "]=1, [" this "]=1, [" that "]=1, ["The "]=1, ["Use "]=1, ["Get "]=1,
  ["Complete "]=1, ["Obtain "]=1, ["Unlock"]=1, ["Reach "]=1, ["Increase"]=1 }
local function scan_capture(v)
  if type(v) ~= "string" then return end
  local L = #v
  if L < 4 or L > 2000 then return end
  if v:find("[\228-\233]") then return end
  if v:find("[\195\128-\195\191]") then return end     -- tem acento -> ja e PT
  if not v:find("%a%a%a") then return end
  if v:find("^[/%.#@<]") or v:find("^%u[%u_%d]+$") then return end
  if _G.__scan[v] then return end
  if tl_one(v) ~= v then return end
  -- so captura se PARECE ingles (tem palavra funcional EN)
  local en = false
  for w in pairs(_EN_W) do if v:find(w, 1, true) then en = true break end end
  if not en then return end
  _G.__scan[v] = true
  _G.__scan_n = _G.__scan_n + 1
  _G.__scan_dirty = true
end
local _SCAN_PATH = "C:/Jogos/Game/C7/Saved/Mods/lua/mods/tl_translate/pt/_scan_misses.txt"
local function scan_flush()
  if not _G.__scan_dirty then return end
  _G.__scan_dirty = false
  local out = {}
  for s in pairs(_G.__scan) do out[#out + 1] = (s:gsub("[\r\n]", " ")) end
  pcall(function() T.File.SaveStringContentToFile(table.concat(out, "\n"), _SCAN_PATH) end)
  pcall(function() T.File.SaveStringContentToFile(_SCAN_PATH, table.concat(out, "\n")) end)
end

local function sweep(roots, cap)
  local st = { c = 0, miss = 0 }; local seen = {}; local n = 0
  local function walk(t)
    if type(t) ~= "table" or seen[t] then return end
    seen[t] = true; n = n + 1
    if n > cap then return end
    pcall(function()
      for k, v in pairs(t) do
        local ks = type(k) == "string" and k or ""
        if not SKIP[ks] and ks:sub(1,2) ~= "__" then
          if type(v) == "string" then
            if ok_string(k, v) then
              local p = tl_one(v)
              if p ~= v then
                pcall(function() t[k] = p end); st.c = st.c + 1
              else
                pcall(scan_capture, v)
              end
            end
          elseif type(v) == "table" then walk(v) end
        end
      end
    end)
  end
  for _, r in ipairs(roots) do walk(r) end
  return st.c, st.miss
end

-- cooldown por CONTADOR de execucao (os.time pode ser constante no sandbox)
H.runs = (H.runs or 0) + 1
local now = H.runs

-- ====== RE-WRAP AGRESSIVO do GetLangStr/GetRow (a fonte C++ que o CPDD nao pega)
if not H.lang_rewrapped then
  H.lang_rewrapped = true
  H.lh = 0
  local function tr_ret(r)
    if type(r) == "string" then
      local p = tl_one(r)
      if p ~= r then H.lh = H.lh + 1; return p end
    elseif type(r) == "table" and not rawget(r, "__lr") then
      pcall(function()
        for k, v in pairs(r) do
          if type(v) == "string" then
            local p = tl_one(v)
            if p ~= v then r[k] = p; H.lh = H.lh + 1 end
          end
        end
        rawset(r, "__lr", true)
      end)
    end
    return r
  end
  local function wrap_mgr(m, why)
    if type(m) ~= "table" then return end
    for _, mn in ipairs({ "GetLangStr", "GetLangStrSplit", "GetRow" }) do
      local om = rawget(m, mn)
      if type(om) == "function" and not rawget(m, "__lr_" .. mn) then
        rawset(m, "__lr_" .. mn, true)
        m[mn] = function(self, ...)
          return tr_ret(om(self, ...))
        end
      end
    end
  end
  local G = _G.Game
  if type(G) == "table" then
    wrap_mgr(rawget(G, "TableDataManager"), "TDM")
    wrap_mgr(rawget(G, "TableData"), "TD")
    local tdm = rawget(G, "TableDataManager")
    if type(tdm) == "table" then wrap_mgr(rawget(tdm, "Instance"), "TDM.Inst") end
  end
  wrap_mgr(rawget(_G, "TableDataManager"), "_G.TDM")
  local pl = package.loaded["Framework.Utils.LuaCommon.Managers.TableDataManager"]
  if type(pl) == "table" then
    wrap_mgr(pl, "pkg")
    wrap_mgr(rawget(pl, "TableDataManager"), "pkg.sym")
    wrap_mgr(rawget(pl, "Instance"), "pkg.Inst")
  end

  -- hook do setNamedWidgetText do CPDD (texto fixo tipo "Recommended Builds")
  local cpdd = package.loaded["mods.cpdd_runtime_fixes.Init"]
  local rf = type(cpdd) == "table" and (rawget(cpdd, "runtimeFixes") or cpdd) or nil
  for _, holder in ipairs({ rf, _G.runtimeFixes, _G }) do
    if type(holder) == "table" then
      for _, fn in ipairs({ "setNamedWidgetText", "setPanelWidgetText", "SetNamedWidgetText" }) do
        local o = rawget(holder, fn)
        if type(o) == "function" and not rawget(holder, "__lr_" .. fn) then
          rawset(holder, "__lr_" .. fn, true)
          holder[fn] = function(w, name, text, ...)
            if type(text) == "string" then text = tl_one(text) end
            return o(w, name, text, ...)
          end
        end
      end
    end
  end
end
rep["hp_lang"] = "langstr hits=" .. tostring(H.lh)

if not H.big_done then
  local roots = {}
  for name, mod in pairs(package.loaded) do
    if type(mod) == "table" and type(name) == "string" and #name < 120
       and name ~= "string" and name ~= "table" and name ~= "math" and name ~= "os"
       and name ~= "io" and name ~= "debug" and name ~= "coroutine" and name ~= "bit"
       and name ~= "jit" and name ~= "ffi" and not SKIP[name]
       and not name:find("Cinematic") and not name:find("Sequence")
       and not name:find("StateMachine") and not name:find("Locomotion")
       and not name:find("AnimNotify") and not name:find("Behavior") then
      roots[#roots + 1] = mod
    end
  end
  if type(_G.Game) == "table" then roots[#roots + 1] = _G.Game end
  local c = sweep(roots, 400000)
  H.big_done = true; H.last_sweep = now; H.bf = c
  rep["hp"] = "BIG(v19) c=" .. c
end

-- HOOK GLOBAL: toda classe (em package.loaded) que tenha SetText/SetName/SetContentText
if not H.settext_hooked then
  H.settext_hooked = true
  local nh = 0
  for name, mod in pairs(package.loaded) do
    if type(mod) == "table" then
      -- pega o symbol e a propria tabela
      for _, obj in ipairs({ mod, rawget(mod, (name:match("([^%.]+)$") or "")) }) do
        if type(obj) == "table" then
          for _, mn in ipairs({ "SetText", "SetName", "SetContentText", "SetTitle",
                                "SetStr", "SetRichText", "SetHtmlText", "SetLabelText" }) do
            local om = rawget(obj, mn)
            if type(om) == "function" and not rawget(obj, "__tl_" .. mn) then
              rawset(obj, "__tl_" .. mn, true)
              obj[mn] = function(self, a, ...)
                if type(a) == "string" then a = tl_one(a) end
                return om(self, a, ...)
              end
              nh = nh + 1
            end
          end
        end
      end
    end
  end
  rep["hp_settext"] = "hooked " .. nh .. " setters"
end

-- re-sweep LEVE: so os sistemas de UI de Game.* + modulos de painel.
-- cooldown por contador. cap baixo pra nao dar hitch.
if H.last_sweep and (now - H.last_sweep) < 10 then rep["hp"] = "cd"; return "cd" end
H.last_sweep = now
local roots = {}
if type(_G.Game) == "table" then
  for k, v in pairs(_G.Game) do
    if type(v) == "table" and type(k) == "string"
       and (k:find("System$") or k:find("HUD") or k:find("Panel") or k:find("Mgr$")) then
      roots[#roots + 1] = v
    end
  end
end
for name, mod in pairs(package.loaded) do
  if type(mod) == "table" and type(name) == "string" and #name < 110 then
    local nl = name:lower()
    if nl:find("panel") or nl:find("_item") or nl:find("_view")
       or nl:find("hud") or nl:find("tips") or nl:find("popup")
       or nl:find("tooltip") or nl:find("widget") then
      roots[#roots + 1] = mod
    end
  end
end
local c = sweep(roots, 90000)
H.bf = (H.bf or 0) + c

-- probe: captura strings de avanço/sequencia p/ eu ver
_G.__adv = _G.__adv or {}
if #_G.__adv < 25 and type(_G.Game) == "table" then
  local seen2 = {}
  local function scan(t, d)
    if type(t) ~= "table" or seen2[t] or d > 6 then return end
    seen2[t] = true
    for k, v in pairs(t) do
      if type(v) == "string" and #v > 4 and #v < 90 and v:find("%a%a%a")
         and (v:lower():find("advance") or v:lower():find("sequence")
              or v:lower():find("avanç") or v:lower():find("sequência")
              or v:lower():find("beyonder") or v:lower():find("talent")) then
        if #_G.__adv < 25 then _G.__adv[#_G.__adv + 1] = v:sub(1, 70) end
      elseif type(v) == "table" then scan(v, d + 1) end
    end
  end
  for _, sn in ipairs({ "AdvancementSystem", "SequenceSystem", "PathwaySystem",
      "PromotionSystem", "BeyonderSystem" }) do
    pcall(scan, rawget(_G.Game, sn), 0)
  end
  for i, s in ipairs(_G.__adv) do rep["adv_" .. i] = s end
end

pcall(scan_flush)
rep["hp"] = "re-sweep +" .. c .. " acum=" .. H.bf .. " scan=" .. _G.__scan_n
return "rs " .. c
