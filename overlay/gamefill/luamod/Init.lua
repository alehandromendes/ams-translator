-- tl_translate — camada de tradução PT-BR do Tradutor de Legendas.
-- Carregado via cpdd_user_settings.lua (PersonalLoad). NÃO toca em nenhum arquivo
-- do CPDD: só lê os módulos já carregados e sobrepõe PT por ID, depois do CPDD.
--
--   modo dump   : cria _tl_dump/run  ->  grava [id]="texto atual" de cada módulo
--   modo aplicar: padrão  ->  mescla pt/<modulo>.lua por cima (prioridade alta)

local Loader = _G.LOMModLoader
if type(Loader) ~= "table" then return {} end

local File = import("LuaFunctionLibrary")
local Paths = import("BlueprintPathsLibrary")
local MODS = File.GetFilePath(Paths.ProjectSavedDir()) .. "/Mods/"
local SELF = MODS .. "lua/mods/tl_translate/"
local DUMP = MODS .. "lua/_tl_dump/"

local function log(msg)
  -- Warning/Error passam pelo PerformanceMode do CPDD (que suprime Info)
  local l = (rawget(_G, "Log")) or (rawget(_G, "LaunchLog")) or _G.Log or _G.LaunchLog
  msg = "[tl_translate] " .. tostring(msg)
  if l and l.Warning then l.Warning(msg)
  elseif l and l.Error then l.Error(msg)
  elseif l and l.Info then l.Info(msg)
  elseif type(print) == "function" then print(msg) end
end

-- File.SaveStringContentToFile / MakeDirectory têm assinatura que varia por build
local function save(content, path)
  local parent = path:match("^(.*)[/\\][^/\\]+$")
  if parent and type(File.MakeDirectory) == "function" then
    pcall(File.MakeDirectory, parent)
  end
  for _, fn in ipairs({
    function() return File.SaveStringContentToFile(content, path) end,
    function() return File.SaveStringContentToFile(path, content) end,
    function() return File.SaveStringToFile and File.SaveStringToFile(content, path) end,
    function() return File.SaveStringToFile and File.SaveStringToFile(path, content) end,
  }) do
    local ok = pcall(fn)
    if ok and File.LoadFile(path) == content then return true end
  end
  return false
end

-- módulos que o CPDD traduz (translation-overrides.lua). Overlays têm .data;
-- Overrides às vezes são a tabela direta.
local MODULES = {
  "Data.Excel.LanguageData.StringDB_CN_Data",
  "Data.Excel.LanguageData.StringDB_CN_Data_achievement",
  "Data.Excel.LanguageData.StringDB_CN_Data_asidetalk",
  "Data.Excel.LanguageData.StringDB_CN_Data_aura",
  "Data.Excel.LanguageData.StringDB_CN_Data_beckland",
  "Data.Excel.LanguageData.StringDB_CN_Data_buffappear",
  "Data.Excel.LanguageData.StringDB_CN_Data_buffdata",
  "Data.Excel.LanguageData.StringDB_CN_Data_debug",
  "Data.Excel.LanguageData.StringDB_CN_Data_gossip",
  "Data.Excel.LanguageData.StringDB_CN_Data_guide",
  "Data.Excel.LanguageData.StringDB_CN_Data_itemgift",
  "Data.Excel.LanguageData.StringDB_CN_Data_itemlife",
  "Data.Excel.LanguageData.StringDB_CN_Data_itemnormal",
  "Data.Excel.LanguageData.StringDB_CN_Data_itemoutlook",
  "Data.Excel.LanguageData.StringDB_CN_Data_itemtask",
  "Data.Excel.LanguageData.StringDB_CN_Data_lettertext",
  "Data.Excel.LanguageData.StringDB_CN_Data_loading",
  "Data.Excel.LanguageData.StringDB_CN_Data_main",
  "Data.Excel.LanguageData.StringDB_CN_Data_maintask",
  "Data.Excel.LanguageData.StringDB_CN_Data_manor",
  "Data.Excel.LanguageData.StringDB_CN_Data_monsterskill",
  "Data.Excel.LanguageData.StringDB_CN_Data_newbietask",
  "Data.Excel.LanguageData.StringDB_CN_Data_newspaper",
  "Data.Excel.LanguageData.StringDB_CN_Data_nocamera",
  "Data.Excel.LanguageData.StringDB_CN_Data_oldtalk",
  "Data.Excel.LanguageData.StringDB_CN_Data_othertalk",
  "Data.Excel.LanguageData.StringDB_CN_Data_sidetask",
  "Data.Excel.LanguageData.StringDB_CN_Data_skill",
  "Data.Excel.LanguageData.StringDB_CN_Data_skill1",
  "Data.Excel.LanguageData.StringDB_CN_Data_skill2",
  "Data.Excel.LanguageData.StringDB_CN_Data_skill3",
  "Data.Excel.LanguageData.StringDB_CN_Data_spellfield",
  "Data.Excel.LanguageData.StringDB_CN_Data_talk",
  "Data.Excel.LanguageData.StringDB_CN_Data_talkother",
  "Data.Excel.LanguageData.StringDB_CN_Data_tingen",
  "Data.Excel.LanguageData.StringDB_CN_Data_tingentalk",
  "Data.Excel.LanguageData.StringDB_CN_Data_traingame",
  "Data.Excel.LanguageData.StringDB_CN_Data_trap",
  "Data.Config.StringConst.Language_zhs",
  "Data.Excel.RoleCreateQandAData",
  "Gameplay.Debug.DebugConst",
  "Gameplay.LogicSystem.CreateRole.CreateRoleAnswer_Panel",
  "Launch.I18n.zh",
  "Shared.language_zhs",
}

local function data_of(value)
  if type(value) ~= "table" then return nil end
  local ok, d = pcall(rawget, value, "data")
  if ok and type(d) == "table" then return d end
  return value
end

local function resolve(name)
  local ok0, reg = pcall(function() return _G.Game and _G.Game.loaded end)
  if ok0 and type(reg) == "table" then
    local L = reg[name]
    if L ~= nil then
      local ok, r = pcall(function()
        return L.Ret ~= nil and L.Ret or L.ENV
      end)
      if ok then return data_of(r) end
    end
  end
  if package.loaded[name] ~= nil then return data_of(package.loaded[name]) end
  local ok, v = pcall(require, name)
  if ok then return data_of(v) end
  return nil
end

-- ---------- escrita de string p/ o dump ----------
local function esc(s)
  s = s:gsub("\\", "\\\\"):gsub('"', '\\"')
  s = s:gsub("\n", "\\n"):gsub("\r", "\\r"):gsub("\t", "\\t")
  return s
end
local function keystr(k)
  if type(k) == "number" then return string.format("%.0f", k) end
  return '"' .. esc(tostring(k)) .. '"'
end

-- ---------- modo dump ----------
-- além dos MODULES fixos, varre Game.loaded/package.loaded atrás de qualquer
-- módulo de texto (nome com essas palavras) — pega labels de UI/skill/tags.
local _SCAN = {
  "String", "Text", "Lang", "Const", "Skill", "Widget", "Dialogue", "Talk",
  "Gossip", "Npc", "NPC", "Tips", "Guide", "Letter", "Name", "Desc", "Menu",
  "Loading", "Bubble", "Activity", "Buff", "Quest", "Task", "Excel",
}
local function scan_name(name)
  for _, kw in ipairs(_SCAN) do
    if name:find(kw, 1, true) then return true end
  end
  return false
end

local function dump_table(name, data)
  if type(data) ~= "table" then return 0 end
  local out, n = { "return {" }, 0
  for k, v in pairs(data) do
    if type(v) == "string" and v ~= "" and #v < 8000
       and (type(k) == "number" or type(k) == "string") then
      out[#out + 1] = "  [" .. keystr(k) .. '] = "' .. esc(v) .. '",'
      n = n + 1
    end
  end
  out[#out + 1] = "}"
  if n > 0 and n < 300000 then
    save(table.concat(out, "\n"), DUMP .. name:gsub("[%.%s/\\]", "_") .. ".lua")
  end
  return n
end

local _best = 0
local function do_dump()
  local total, mods = 0, 0
  local done = {}
  local map = { "return {" }   -- sanitizado -> nome real
  local function take(name, data)
    if done[name] then return end
    local n = dump_table(name, data)
    if n > 0 and n < 300000 then
      done[name] = true
      map[#map + 1] = '  ["' .. name:gsub("[%.%s/\\]", "_") .. '"] = "'
                      .. esc(name) .. '",'
      total = total + n
      mods = mods + 1
    end
  end
  -- catálogo COMPLETO: todo módulo carregado + nº de strings + 1 amostra.
  -- serve pra achar em que módulo um texto visível realmente mora.
  -- TUDO em pcall — objetos UE explodem em acessos triviais.
  local cat = { "# src modulo | strings | amostra" }
  local function scan_one(src, name, L)
    local d
    if type(L) == "table" then
      local ret = rawget(L, "Ret")
      local env = rawget(L, "ENV")
      d = (type(ret) == "table" and ret) or (type(env) == "table" and env) or L
    else
      return
    end
    if type(d) ~= "table" then return end
    local dd = rawget(d, "data")
    if type(dd) == "table" then d = dd end
    local ns, sample = 0, ""
    for k, v in pairs(d) do
      if type(v) == "string" and #v > 1 and #v < 4000 then
        ns = ns + 1
        if sample == "" and #v < 90 then sample = v end
      end
    end
    if ns > 0 then
      cat[#cat + 1] = src .. " " .. name .. " | " .. ns .. " | " .. esc(sample)
    end
  end
  local function catalog(reg, src)
    if type(reg) ~= "table" then return end
    for name, L in pairs(reg) do
      if type(name) == "string" then pcall(scan_one, src, name, L) end
    end
  end
  -- 1) dump dos MODULES fixos + varredura por palavra-chave (o essencial)
  for _, name in ipairs(MODULES) do pcall(take, name, resolve(name)) end
  local function safe_data(L)
    if type(L) ~= "table" then return nil end
    local ret = rawget(L, "Ret"); if type(ret) == "table" then return data_of(ret) end
    local env = rawget(L, "ENV"); if type(env) == "table" then return data_of(env) end
    return data_of(L)
  end
  local reg = _G.Game and _G.Game.loaded
  if type(reg) == "table" then
    for name, L in pairs(reg) do
      if type(name) == "string" and not done[name] and scan_name(name) then
        local ok, d = pcall(safe_data, L)
        if ok then pcall(take, name, d) end
      end
    end
  end
  for name, v in pairs(package.loaded) do
    if type(name) == "string" and not done[name] and scan_name(name) then
      local ok, d = pcall(function() return data_of(v) end)
      if ok then pcall(take, name, d) end
    end
  end
  map[#map + 1] = "}"
  save(table.concat(map, "\n"), DUMP .. "_modules.lua")
  if total > _best then _best = total end
  save("done modules=" .. mods .. " entries=" .. total
       .. " best=" .. _best, DUMP .. "status")
  log("DUMP: " .. mods .. " modulos, " .. total .. " entradas -> " .. DUMP)

  -- 2) catálogo completo (best-effort — não pode derrubar o dump)
  pcall(function()
    pcall(catalog, _G.Game and _G.Game.loaded, "G")
    pcall(catalog, package.loaded, "P")
    save(table.concat(cat, "\n"), DUMP .. "_catalog.txt")
  end)
end

-- ---------- modo aplicar ----------
local pt_cache = {}
local function sanitize(name)
  return (name:gsub("[%.%s/\\]", "_"))
end

local function pt_for(name)
  if pt_cache[name] ~= nil then return pt_cache[name] end
  local path = SELF .. "pt/" .. sanitize(name) .. ".lua"
  local src = File.LoadFile(path)
  local tbl = false
  if src and src ~= "" then
    local chunk = load(src, "@" .. path)
    if chunk then
      local ok, v = pcall(chunk)
      if ok and type(v) == "table" then tbl = v end
    end
  end
  pt_cache[name] = tbl
  return tbl
end

local _applied = {}   -- name -> entradas mescladas na última passada
local _report = {}    -- linhas de diagnóstico p/ disco
local _call_counts = {}   -- método do manager -> nº chamadas (diag)
local _langstr_samples = 0

local function apply_one(name, value)
  local pt = pt_for(name)
  if pt == false then
    _report[name] = "pt=FALHOU_CARREGAR"
    return value
  end
  if not pt then _report[name] = "pt=vazio"; return value end
  local data = data_of(value)
  if type(data) ~= "table" then
    _report[name] = "value_sem_data (" .. type(value) .. ")"
    return value
  end
  local n, hit = 0, 0
  for k, v in pairs(pt) do
    if type(v) == "string" and v ~= "" then
      if data[k] ~= nil then hit = hit + 1 end
      data[k] = v
      n = n + 1
    end
  end
  _applied[name] = n
  _report[name] = "ok n=" .. n .. " (chaves ja existentes=" .. hit .. ")"
  if n > 0 then log("apply " .. name .. " = " .. n) end
  return value
end

-- lista de módulos a aplicar: pt/_index.lua (nomes reais gravados pelo build)
-- com fallback pra MODULES fixo.
local APPLY_LIST = MODULES
do
  local src = File.LoadFile(SELF .. "pt/_index.lua")
  if src and src ~= "" then
    local chunk = load(src, "@_index")
    if chunk then
      local ok, v = pcall(chunk)
      if ok and type(v) == "table" and #v > 0 then APPLY_LIST = v end
    end
  end
end

local function write_apply_status()
  local lines = { "tl_translate APPLY status  (" .. #APPLY_LIST .. " modulos)" }
  local total = 0
  local shown = {}
  for _, name in ipairs(APPLY_LIST) do
    lines[#lines + 1] = name .. "  ->  " .. (_report[name] or "NAO_CHAMADO")
    total = total + (_applied[name] or 0)
    shown[name] = true
  end
  for name, rep in pairs(_report) do
    if not shown[name] then
      lines[#lines + 1] = name .. "  ->  " .. rep
      total = total + (_applied[name] or 0)
    end
  end
  lines[#lines + 1] = "TOTAL entradas mescladas = " .. total
  -- diagnóstico: quais getters do manager foram chamados
  local cc = {}
  for k, v in pairs(_call_counts) do cc[#cc + 1] = { k, v } end
  table.sort(cc, function(a, b) return a[2] > b[2] end)
  lines[#lines + 1] = "--- chamadas de getter ---"
  for i = 1, math.min(#cc, 25) do
    lines[#lines + 1] = "  " .. cc[i][1] .. " = " .. cc[i][2]
  end
  save(table.concat(lines, "\n"), SELF .. "apply_status.txt")
end

-- ---------------------------------------------------------------
-- File.LoadFile devolve "" (não nil) quando o arquivo não existe.
local _runf = File.LoadFile(DUMP .. "run")
local dump_mode = _runf ~= nil and _runf ~= ""
log("carregado, dump_mode=" .. tostring(dump_mode))

if dump_mode then
  -- do_dump força require dos 45 módulos. Roda já e de novo nas fases —
  -- cada passada reescreve os arquivos, a que pegar mais módulos ganha.
  pcall(do_dump)
  pcall(function()
    Loader.On("after_prepare", do_dump, 9000000, "tl_translate.dump.prepare")
    Loader.On("after_main", do_dump, 9000000, "tl_translate.dump.main")
  end)
else
  for _, name in ipairs(APPLY_LIST) do
    Loader.AfterLoad(name, function(v) return apply_one(name, v) end,
                     8000000, "tl_translate.apply." .. name)
  end

  -- ============ INJEÇÃO NO cpdd_translation (o ponto onde o CPDD lê) ========
  -- translateVisibleText -> directLookup -> getDirectTable(tag) ->
  --   Loader.LoadExternal("cpdd_translation.Data.Excel.LanguageData.StringDB_CN_Data_<tag>")
  -- LoadExternal devolve Loader.ExternalLoaded[name] se já existir. A gente
  -- pré-preenche isso AGORA (PersonalLoad roda antes do game main) com PT.
  local BASE_EXT = "cpdd_translation.Data.Excel.LanguageData.StringDB_CN_Data"
  local _cpdd_tables = {}   -- nome_externo -> data map PT (carregado 1x)
  local _pt_by_tag = {}     -- tag ("" p/ agregado) -> {[id]="pt"}
  local _getrow_hits = 0
  local _getrow_field_hits = 0
  local _en2pt_lookup            -- forward: função (en) -> pt|nil, definida depois
  local _ROW_FIELDS = {
    Name = true, Title = true, Desc = true, Description = true, Text = true,
    Content = true, Tip = true, Tips = true, SubName = true, ShortName = true,
    Summary = true, Detail = true, Details = true, Label = true, Comment = true,
    Target = true, TargetDesc = true, RewardDesc = true, UIName = true,
    DisplayName = true, TabName = true, GroupName = true, BtnName = true,
  }
  do
    local tags = {}
    local tsrc = File.LoadFile(SELF .. "pt/cpdd_tags.lua")
    if tsrc and tsrc ~= "" then
      local ch = load(tsrc, "@cpdd_tags")
      if ch then local ok, v = pcall(ch); if ok and type(v) == "table" then tags = v end end
    end
    local okt, failt, agg_n = 0, 0, 0
    for _, tag in ipairs(tags) do
      local stem = "cpdd_" .. (tag ~= "" and tag or "AGG")
      local src = File.LoadFile(SELF .. "pt/" .. stem .. ".lua")
      if src and src ~= "" then
        local ch, cerr = load(src, "@" .. stem)
        if ch then
          local ok, data = pcall(ch)
          if ok and type(data) == "table" then
            _cpdd_tables[BASE_EXT .. (tag ~= "" and ("_" .. tag) or "")] = data
            _pt_by_tag[tag] = data
            okt = okt + 1
            if tag == "" then for _ in pairs(data) do agg_n = agg_n + 1 end end
          else failt = failt + 1 end
        else
          failt = failt + 1
          if failt == 1 then _report["cpdd_tag_load_err"] = tostring(cerr):sub(1, 80) end
        end
      end
    end
    _report["pt_by_tag"] = "tags ok=" .. okt .. " falha=" .. failt
      .. " | AGG entradas=" .. agg_n
  end

  -- ============ INTERCEPTA manager:GetRow (a fonte REAL do texto) ===========
  -- O jogo pega texto via TableDataManager:GetRow("LanguageData.StringDB_CN_Data_<tag>", id)
  -- que lê do Game.TableData (C++, já em INGLÊS). O CPDD embrulha esse GetRow
  -- mas o repairLiveString dele desiste em texto sem CJK (linha ~2051), então
  -- inglês passa reto. A gente embrulha Por CIMA do CPDD (prioridade alta =
  -- roda por último = mais externo) e devolve PT quando temos.
  local _LANG_PREFIX = "LanguageData.StringDB_CN_Data"
  local function pt_row(tableName, rowKey)
    if type(tableName) ~= "string" or tableName:sub(1, #_LANG_PREFIX) ~= _LANG_PREFIX then
      return nil
    end
    local suffix = tableName:sub(#_LANG_PREFIX + 1)
    local tag = (suffix:sub(1, 1) == "_") and suffix:sub(2) or ""
    local t = _pt_by_tag[tag] or _pt_by_tag[""]
    if type(t) ~= "table" then return nil end
    local v = t[rowKey]
    if v == nil and type(rowKey) == "number" then
      v = t[string.format("%.0f", rowKey)]
    end
    return v
  end
  -- traduz os campos-string de uma ROW via mapa EN->PT (in place, 1x)
  local _row_samples = 0
  local function translate_row(row)
    if type(row) ~= "table" or rawget(row, "__tl_pt") or not _en2pt_lookup then
      return row
    end
    pcall(function()
      local sample_keys
      for k, v in pairs(row) do
        if type(v) == "string" and #v > 1 and #v < 4000 then
          if _row_samples < 6 then
            sample_keys = (sample_keys or "") .. tostring(k) .. "=" .. v:sub(1, 22) .. " | "
          end
          local p = _en2pt_lookup(v)
          if p then row[k] = p; _getrow_field_hits = _getrow_field_hits + 1 end
        end
      end
      if sample_keys and _row_samples < 6 then
        _row_samples = _row_samples + 1
        _report["row_sample_" .. _row_samples] = sample_keys
      end
      rawset(row, "__tl_pt", true)
    end)
    return row
  end

  -- PT por (id, tag). tag "" = agregado. cai pra string key se preciso.
  local function pt_id(index, tag)
    local t = _pt_by_tag[tag or ""] or _pt_by_tag[""]
    if type(t) ~= "table" then return nil end
    local v = t[index]
    if v == nil and type(index) == "number" then
      v = t[string.format("%.0f", index)]
    elseif v == nil and type(index) == "string" then
      v = t[tonumber(index) or index]
    end
    return v
  end

  -- ---- roda pt/hotpatch.lua ----
  -- DEV (marca _tl_dump/.dev ou _tl_dump/run existe): recarrega FRESCO do disco
  --   a cada 300 ticks — permite editar o hotpatch sem reiniciar o jogo.
  -- PRODUÇÃO (usuário final): compila UMA vez, reusa, e roda a cada 2000 ticks
  --   — zero I/O por tick e cadência baixa pra NÃO dar hitch no jogo.
  local _hp_tick, _hp_chunk = 0, nil
  local _dev = ((File.LoadFile(DUMP .. "run") or "") ~= "")
    or ((File.LoadFile(DUMP .. ".dev") or "") ~= "")
  _G.__hp = _G.__hp or {}
  _G.__hp._dev = _dev
  _G.__hp._dumpdir = DUMP
  local HP_EVERY = _dev and 300 or 2000
  local HP_PATH = File.GetFilePath(Paths.ProjectSavedDir())
    .. "/Mods/lua/mods/tl_translate/pt/hotpatch.lua"
  local function hot_check()
    _hp_tick = _hp_tick + 1
    -- primeira passada cedo (tick 120), depois na cadência
    if _hp_tick ~= 120 and _hp_tick % HP_EVERY ~= 0 then return end
    local chunk = _hp_chunk
    if _dev or not chunk then
      chunk = nil
      if _dev and type(loadfile) == "function" then
        chunk = loadfile(HP_PATH)                     -- fresh do disco (dev)
      end
      if not chunk then
        local src = File.LoadFile(SELF .. "pt/hotpatch.lua")
        if src and src ~= "" then chunk = load(src, "@hotpatch") end
      end
      if not _dev then _hp_chunk = chunk end          -- cacheia em produção
    end
    if not chunk then return end
    local ok, res = pcall(chunk)
    _report["hotpatch"] = ok and ("ok: " .. tostring(res))
      or ("run err: " .. tostring(res):sub(1, 60))
    if _dev then pcall(write_apply_status) end
  end

  local function bump(name)
    _call_counts[name] = (_call_counts[name] or 0) + 1
    hot_check()
  end

  -- pós-processa QUALQUER retorno de um getter: string -> en2pt; table -> campos
  local function pt_out(r)
    if type(r) == "string" then
      local p = _en2pt_lookup and _en2pt_lookup(r)
      if p then _getrow_field_hits = _getrow_field_hits + 1; return p end
      return r
    elseif type(r) == "table" then
      return translate_row(r)
    end
    return r
  end

  local _mgr_wrapped = {}
  local function wrap_getrow(mgr, why)   -- embrulha TODOS os Get*/Query* do manager
    if type(mgr) ~= "table" or _mgr_wrapped[mgr] then return end
    _mgr_wrapped[mgr] = true
    local hooked = 0

    -- GetRow: PT por (tableName,id) + tradução de row
    local oRow = rawget(mgr, "GetRow") or mgr.GetRow
    if type(oRow) == "function" then
      mgr.GetRow = function(self, tableName, rowKey, priority)
        bump("GetRow")
        local pt = pt_row(tableName, rowKey)
        if pt ~= nil then _getrow_hits = _getrow_hits + 1; return pt end
        return pt_out(oRow(self, tableName, rowKey, priority))
      end
      hooked = hooked + 1
    end
    -- GetLangStr / GetLangStrSplit: PT por id
    local oLang = rawget(mgr, "GetLangStr") or mgr.GetLangStr
    if type(oLang) == "function" then
      mgr.GetLangStr = function(self, index)
        bump("GetLangStr")
        local pt = pt_id(index, "")
        if pt ~= nil then _getrow_hits = _getrow_hits + 1; return pt end
        local raw = oLang(self, index)
        -- amostra de diagnóstico: 8 primeiras chamadas
        if _langstr_samples < 8 then
          _langstr_samples = _langstr_samples + 1
          local has = (type(raw) == "string" and _en2pt_lookup and _en2pt_lookup(raw)) and "SIM" or "nao"
          _report["langstr_sample_" .. _langstr_samples] =
            "idx=" .. tostring(index) .. " (" .. type(index) .. ") raw=" ..
            tostring(type(raw) == "string" and raw:sub(1, 30) or type(raw)) ..
            " en2pt=" .. has
        end
        return pt_out(raw)
      end
      hooked = hooked + 1
    end
    local oSplit = rawget(mgr, "GetLangStrSplit") or mgr.GetLangStrSplit
    if type(oSplit) == "function" then
      mgr.GetLangStrSplit = function(self, index, tag)
        bump("GetLangStrSplit")
        local pt = pt_id(index, tag)
        if pt ~= nil then _getrow_hits = _getrow_hits + 1; return pt end
        return pt_out(oSplit(self, index, tag))
      end
      hooked = hooked + 1
    end
    -- todos os outros Get*Row / Get*Data / Query* / GetString* : traduz o retorno
    for k, fn in pairs(mgr) do
      if type(k) == "string" and type(fn) == "function"
         and k ~= "GetRow" and k ~= "GetLangStr" and k ~= "GetLangStrSplit"
         and (k:match("^Get.-Row$") or k:match("^Get.-Data$")
              or k:match("^GetString") or k:match("^Query")
              or k:match("Localiz") or k:match("^GetText")) then
        local orig = fn
        local kk = k
        mgr[k] = function(self, ...)
          bump(kk)
          return pt_out(orig(self, ...))
        end
        hooked = hooked + 1
      end
    end

    if hooked > 0 then
      _report["mgr@" .. tostring(why)] = "wrapped " .. hooked .. " métodos"
      log("manager wrapped (" .. tostring(why) .. "): " .. hooked)
    end
  end

  -- injeta/re-mescla em Loader.ExternalLoaded. Roda no load E nas fases —
  -- se o CPDD já carregou o bytecode antes, a gente mescla PT por cima da .data.
  local function inject_cpdd(probe)
    Loader.ExternalLoaded = Loader.ExternalLoaded or {}
    local hit, merged, probed = 0, 0, "?"
    for name, data in pairs(_cpdd_tables) do
      local ex = Loader.ExternalLoaded[name]
      if ex == nil then
        Loader.ExternalLoaded[name] = { data = data }
        hit = hit + 1
      else
        local d = (type(ex) == "table" and rawget(ex, "data")) or ex
        if type(d) == "table" then
          local ok = pcall(function()
            for k, v in pairs(data) do d[k] = v end
          end)
          if ok then merged = merged + 1 end
        end
      end
    end
    if probe then
      -- confere se o CPDD realmente lê a nossa tabela agregada
      local agg = Loader.ExternalLoaded[BASE_EXT]
      local ad = agg and ((type(agg) == "table" and rawget(agg, "data")) or agg)
      if type(ad) == "table" then
        -- "Undercurrent Crisis" id do dump agregado
        local s = ad[879817876572416]
        probed = tostring(s):sub(1, 40)
      end
    end
    _report["cpdd_translation.*"] = "inj novo=" .. hit .. " merge=" .. merged
      .. " probe[879817876572416]=" .. probed
    _applied["cpdd_translation.*"] = hit + merged
    log("cpdd_translation: novo=" .. hit .. " merge=" .. merged .. " probe=" .. probed)
  end
  pcall(inject_cpdd, false)

  -- ---- camada EN->PT no geminiTextOverrides do CPDD ----------------
  -- translateVisibleText(txt) do CPDD faz geminiTextOverrides[txt]. O CPDD
  -- resolve muita coisa pra INGLÊS na camada de dados antes disso. Ao fundir
  -- nosso mapa EN->PT na tabela do RuntimeTextGemini, todo texto que o CPDD
  -- deixou em inglês passa a ser re-traduzido pra PT nesse mesmo lookup.
  local GEMINI = "mods.cpdd_runtime_fixes.RuntimeTextGemini"
  local _en2pt, _en2pt_n = nil, 0
  local function load_en2pt()
    if _en2pt ~= nil then return _en2pt end
    _en2pt = false
    local nsrc = File.LoadFile(SELF .. "pt/_en2pt_count.lua")
    local nparts = 0
    if nsrc and nsrc ~= "" then
      local ch = load(nsrc, "@n")
      if ch then local ok, v = pcall(ch); if ok then nparts = tonumber(v) or 0 end end
    end
    if nparts < 1 then
      _report["en2pt"] = "count invalido (" .. tostring(nparts) .. ")"
      return _en2pt
    end
    local acc = {}
    local okp, failp = 0, 0
    for i = 1, nparts do
      local src = File.LoadFile(SELF .. "pt/_en2pt_" .. i .. ".lua")
      if src and src ~= "" then
        local chunk, cerr = load(src, "@_en2pt_" .. i)
        if chunk then
          local ok, v = pcall(chunk)
          if ok and type(v) == "table" then
            okp = okp + 1
            for k, pv in pairs(v) do acc[k] = pv; _en2pt_n = _en2pt_n + 1 end
          else
            failp = failp + 1
          end
        else
          failp = failp + 1
          if failp == 1 then _report["en2pt_load_err"] = tostring(cerr):sub(1, 80) end
        end
      end
    end
    if _en2pt_n > 0 then _en2pt = acc end
    _report["en2pt"] = "chunks ok=" .. okp .. " falha=" .. failp .. " pares=" .. _en2pt_n
    return _en2pt
  end
  local function merge_gemini(value)
    local map = load_en2pt()
    if type(map) ~= "table" or type(value) ~= "table" then return value end
    local n = 0
    for k, v in pairs(map) do
      if value[k] == nil then value[k] = v; n = n + 1 end
    end
    _report[GEMINI] = "en2pt merge n=" .. n .. " (mapa=" .. _en2pt_n .. ")"
    _applied[GEMINI] = n
    log("gemini EN->PT merge = " .. n)
    return value
  end
  Loader.AfterLoad(GEMINI, merge_gemini, 8000000, "tl_translate.gemini_en2pt")
  do
    local seen = false
    for _, nm in ipairs(APPLY_LIST) do if nm == GEMINI then seen = true break end end
    if not seen then APPLY_LIST[#APPLY_LIST + 1] = GEMINI end
  end

  -- liga o mapa EN->PT ao tradutor de campos de ROW (translate_row)
  _en2pt_lookup = function(en)
    local m = load_en2pt()
    return type(m) == "table" and m[en] or nil
  end

  -- expõe o kit interno pro hotpatch.lua (iteração sem restart)
  _G.__tl = {
    en2pt = function(s) return _en2pt_lookup(s) end,
    pt_id = pt_id,
    pt_row = pt_row,
    translate_row = translate_row,
    wrap_mgr = wrap_getrow,
    pt_by_tag = _pt_by_tag,
    report = _report,
    counts = _call_counts,
    G = _G, Loader = Loader, File = File,
    load_en2pt = load_en2pt,
  }

  -- ============ CATCH-ALL: traduz o texto que chega nos componentes de UI =====
  -- CPDD engancha essas classes p/ "reparar" texto CN->EN. A gente engancha
  -- POR CIMA (prioridade alta) e troca EN->PT no argumento dos setters de texto.
  local _ui_hits = 0
  local _UI_TEXT_METHODS = {
    "SetText", "SetName", "SetContentText", "SetTitle", "SetLabelText",
    "SetContent", "SetStr", "SetRichText", "SetHtmlText", "SetDisplayText",
  }
  local _UI_CLASSES = {
    { "Framework.KGFramework.KGUI.Component.Button.UIComText", "UIComText" },
    { "Framework.KGFramework.KGUI.Component.Button.UIComButton", "UIComButton" },
    { "Framework.KGFramework.KGUI.Component.Select.UIComDropDown", "UIComDropDown" },
    { "Framework.KGFramework.KGUI.Component.Select.UIComDropDownItem", "UIComDropDownItem" },
    { "Framework.KGFramework.KGUI.Component.Tab.UIComTabList", "UIComTabList" },
    { "Framework.KGFramework.KGUI.Component.Tab.UIComSimpleTabList", "UIComSimpleTabList" },
    { "Framework.KGFramework.KGUI.Component.Tab.UIComTabItem", "UIComTabItem" },
    { "Framework.KGFramework.KGUI.Component.Tools.UIComDiyTitle", "UIComDiyTitle" },
    { "Framework.KGFramework.KGUI.Widget.KGTextBlock", "KGTextBlock" },
    { "Framework.KGFramework.KGUI.Widget.KGRichTextBlock", "KGRichTextBlock" },
    { "Gameplay.LogicSystem.Lib.LibText", "LibText" },
  }
  local _ui_wrapped = {}
  local function tl_text(s)
    if type(s) ~= "string" or #s < 2 or #s > 4000 then return s end
    local p = _en2pt_lookup and _en2pt_lookup(s)
    if p then _ui_hits = _ui_hits + 1; return p end
    return s
  end
  local function wrap_ui_class(cls, why)
    if type(cls) ~= "table" or _ui_wrapped[cls] then return end
    _ui_wrapped[cls] = true
    local n = 0
    for _, mname in ipairs(_UI_TEXT_METHODS) do
      local orig = rawget(cls, mname)
      if type(orig) == "function" then
        cls[mname] = function(self, a, ...)
          return orig(self, tl_text(a), ...)
        end
        n = n + 1
      end
    end
    if n > 0 then
      _report["ui@" .. tostring(why)] = "wrapped " .. n .. " setters"
    end
  end
  for _, spec in ipairs(_UI_CLASSES) do
    local mod, sym = spec[1], spec[2]
    Loader.AfterLoad(mod, function(v, env)
      local cls = (type(v) == "table" and rawget(v, sym))
        or (type(env) == "table" and env[sym]) or v
      pcall(wrap_ui_class, cls, sym)
      pcall(wrap_ui_class, v, sym .. ".v")
      return v
    end, 9000000, "tl_translate.ui." .. mod:gsub("[^%w]", "-"))
  end

  -- embrulha o GetRow onde quer que ele apareça
  local function wrap_all_getrows()
    pcall(function()
      if _G.Game then
        wrap_getrow(_G.Game.TableDataManager, "Game.TableDataManager")
        wrap_getrow(_G.Game.TableData, "Game.TableData")
        if type(_G.Game.TableDataManager) == "table" then
          wrap_getrow(rawget(_G.Game.TableDataManager, "Instance"), "GTDM.Instance")
        end
      end
      wrap_getrow(rawget(_G, "TableDataManager"), "_G.TableDataManager")
      if package.loaded["Framework.Utils.LuaCommon.Managers.TableDataManager"] then
        wrap_getrow(package.loaded["Framework.Utils.LuaCommon.Managers.TableDataManager"],
                    "pkg.TableDataManager")
      end
    end)
  end
  Loader.AfterLoad("Framework.Utils.LuaCommon.Managers.TableDataManager", function(v, env)
    -- mesmo getSymbol que o CPDD usa pra achar o objeto real
    local mgr = (type(v) == "table" and rawget(v, "TableDataManager"))
      or (type(env) == "table" and env.TableDataManager)
      or (rawget(_G, "TableDataManager"))
      or v
    pcall(wrap_getrow, mgr, "TableDataManager")
    pcall(wrap_getrow, v, "TableDataManager.value")
    if type(mgr) == "table" and type(rawget(mgr, "Instance")) == "table" then
      pcall(wrap_getrow, mgr.Instance, "TableDataManager.Instance")
    end
    return v
  end, 9000000, "tl_translate.getrow.manager")
  Loader.AfterLoad("Data.Excel.TableData", function(v)
    pcall(wrap_getrow, v, "AfterLoad.Data.Excel.TableData")
    return v
  end, 9000000, "tl_translate.getrow.tabledata")
  -- carrega já todos os pt/ (mede falhas de load na hora)
  local _loadok, _loadfail = 0, 0
  for _, name in ipairs(APPLY_LIST) do
    if pt_for(name) then _loadok = _loadok + 1 else _loadfail = _loadfail + 1 end
  end
  log("pt/ carregados ok=" .. _loadok .. " falha=" .. _loadfail)
  -- força o require de cada módulo StringDB + aplica na hora. getDirectTable
  -- do CPDD faz o mesmo require lazy; a gente antecipa pra o hook/reapply pegar.
  local function force_apply_all()
    for _, name in ipairs(APPLY_LIST) do
      local ok, m = pcall(require, name)
      if ok and type(m) == "table" then
        pcall(apply_one, name, m)
      else
        pcall(Loader.Reapply, name)
      end
    end
  end

  Loader.On("after_prepare", function()
    pcall(load_en2pt)                -- aquece o mapa EN->PT (fora do hot path)
    pcall(inject_cpdd, true)
    pcall(wrap_all_getrows)
    pcall(force_apply_all)
    pcall(write_apply_status)
  end, 8000000, "tl_translate.reapply.prepare")
  Loader.On("after_main", function()
    pcall(load_en2pt)
    pcall(inject_cpdd, true)
    pcall(wrap_all_getrows)
    pcall(force_apply_all)
    _report["GetRow hits"] = tostring(_getrow_hits)
    _report["GetRow field hits"] = tostring(_getrow_field_hits)
    _report["UI setter hits"] = tostring(_ui_hits)
    pcall(function()
      _report["probe_en2pt"] =
        "'Undercurrent Crisis'=" .. tostring(_en2pt_lookup("Undercurrent Crisis")) ..
        " | 'Exit Game'=" .. tostring(_en2pt_lookup("Exit Game")) ..
        " | 'Confirm'=" .. tostring(_en2pt_lookup("Confirm")) ..
        " | 'Dungeon'=" .. tostring(_en2pt_lookup("Dungeon"))
    end)
    pcall(write_apply_status)
    log("PT layer active — GetRow hits=" .. _getrow_hits)
  end, 9000000, "tl_translate.reapply.main")
end

return {}
