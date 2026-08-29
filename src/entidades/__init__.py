"""
Módulo de Entidades — Protocolo: Batata
"""
from src.entidades.jogador import Jogador
from src.entidades.projetil import Projetil
from src.entidades.inimigo_base import InimigoBase
from src.entidades.inimigo_padrao import InimigoPadrao
from src.entidades.inimigo_rapido import InimigoRapido
from src.entidades.inimigo_phasing import InimigoPhasing
from src.entidades.inimigo_blindado import InimigoBlindado
from src.entidades.inimigo_ranged import InimigoRanged
from src.entidades.inimigo_tank import InimigoTank

__all__ = [
    "Jogador", "Projetil", "InimigoBase", "InimigoPadrao",
    "InimigoRapido", "InimigoPhasing", "InimigoBlindado",
    "InimigoRanged", "InimigoTank"
]
