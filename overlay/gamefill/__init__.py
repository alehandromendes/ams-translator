"""
@description Preenche as lacunas de tradução do mod de localização de Lord of Mysteries
             (诡秘之主): acha as strings de diálogo que ainda têm chinês, traduz com o
             mesmo motor + glossário do tradutor de legendas e grava um overlay .lua
             que o próprio mod carrega por cima. Re-executável.
@connects usa overlay.translator + glossary/*.csv; mexe SÓ em
          <jogo>/C7/Saved/Mods/localization/  (pasta do usuário, fora dos .pak)
"""
from .core import GameFill, DIALOGUE_MODULES, find_mod_dir

__all__ = ["GameFill", "DIALOGUE_MODULES", "find_mod_dir"]
