"""
Módulo de Equipamentos e Drones Companheiros — Protocolo: Batata
"""

from src.equipamentos.drone_base import DroneBase
from src.equipamentos.drone_cura import DroneCura
from src.equipamentos.drone_combate import DroneCombate
from src.equipamentos.drone_suporte import DroneSuporte

__all__ = [
    "DroneBase",
    "DroneCura",
    "DroneCombate",
    "DroneSuporte"
]
