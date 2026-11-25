"""
Módulo de Armas — Protocolo: Batata
"""
from src.armas.arma_base import ArmaBase
from src.armas.pistola import Pistola
from src.armas.melee import Melee
from src.armas.minigun import Minigun
from src.armas.shotgun import Shotgun
from src.armas.rifle_assalto import RifleAssalto
from src.armas.lanca_foguetes import LancaFoguetes
from src.armas.lanca_granadas import LancaGranadas
from src.armas.railgun import Railgun
from src.armas.bastao_choque import BastaoChoque
from src.armas.smg_compacta import SMGCompacta
from src.armas.rifle_arco import RifleArco
from src.armas.lanca_chamas import LancaChamas

__all__ = [
    "ArmaBase", "Pistola", "Melee", "BastaoChoque", "SMGCompacta",
    "Minigun", "Shotgun", "RifleAssalto",
    "LancaFoguetes", "LancaGranadas", "Railgun",
    "RifleArco", "LancaChamas",
]

