"""
Gerador Determinístico de Sprites em Pixel Art Limpo — Protocolo: Batata
Cria e armazena em cache superfícies Pygame (16x16, 20x20, 24x24 escaladas por inteiro)
com contorno escuro de 1px (#141820) e paleta controlada para:
- Cleiton (Batata) com frames de caminhada/pulo e dano
- 6 Inimigos do Escritório (Gabinete, Mouse Óptico, Copiadora Xerox, Monitor CRT, Triturador, Projetor Laser)
- 4 Mini-Bosses do Escritório (Impressora Matricial, Fonte Genérica 500W, Roteador Corporativo, No-Break Chumbado)
- Caixa de Som (Totem destrutível da Geladeira Tsunami)
- 3 Drones Companheiros com evolução visual MK-I, MK-II e MK-III
- 8 Armas e Ícones de Drops / Cápsulas de Suprimento
NOTA: O Chefe Final (Geladeira Tsunami) NUNCA é interceptado por este módulo e preserva seu PNG original.
"""

import pygame

PALETA_PIXEL = {
    "O": (20, 24, 32, 255),       # Contorno escuro 1px
    "W": (255, 255, 255, 255),    # Branco puro
    "K": (15, 23, 42, 255),       # Azul-noite muito escuro
    # Batata (Cleiton)
    "Y": (229, 169, 60, 255),     # Corpo batata dourado
    "H": (247, 203, 107, 255),    # Brilho batata claro
    "D": (184, 125, 36, 255),     # Sombra batata
    "P": (168, 85, 247, 255),     # Faixa tecnológica roxa
    "L": (216, 180, 254, 255),    # Brilho roxo claro
    # Metais e Escritório
    "M": (100, 116, 139, 255),    # Metal médio
    "S": (148, 163, 184, 255),    # Metal claro / prata
    "Z": (51, 65, 85, 255),       # Metal escuro / chassi
    # Acentos luminosos
    "R": (225, 29, 72, 255),      # Vermelho laser / LED
    "F": (251, 113, 133, 255),    # Vermelho claro
    "G": (34, 197, 94, 255),      # Verde cura
    "E": (134, 239, 172, 255),    # Verde claro
    "C": (56, 189, 248, 255),     # Ciano elétrico / estase
    "A": (186, 230, 253, 255),    # Ciano claro
    "N": (249, 115, 22, 255),     # Laranja alerta / brasa
    "U": (250, 204, 21, 255),     # Amarelo ouro / XP
}

# 1. CLEITON (BATATA) - Matriz 16x16
GRID_BATATA_IDLE = [
    ".....OOOOOO.....",
    "...OOYYYYYYOO...",
    "..OYYYYHYYYYYO..",
    ".OYYYHYYYYYYYYO.",
    ".OYYYYYYYYYYYYO.",
    "OYYYYOOWYYYYOOWO",
    "OYYYYOOKYYYYOOKO",
    "OPPPPPPLLLPPPPPO",
    "OYYYYYYYYYYYYYYO",
    "OYYYYDDDDDDYYYYO",
    ".OYYYYDDDDYYYYO.",
    ".OYYYYDDDDYYYYO.",
    "..OYYYYYYYYYYO..",
    "...OOYYYYYYOO...",
    "....OO....OO....",
    "....OO....OO....",
]

GRID_BATATA_WALK = [
    ".....OOOOOO.....",
    "...OOYYYYYYOO...",
    "..OYYYYHYYYYYO..",
    ".OYYYHYYYYYYYYO.",
    ".OYYYYYYYYYYYYO.",
    "OYYYYOOWYYYYOOWO",
    "OYYYYOOKYYYYOOKO",
    "OPPPPPPLLLPPPPPO",
    "OYYYYYYYYYYYYYYO",
    "OYYYYDDDDDDYYYYO",
    ".OYYYYDDDDYYYYO.",
    ".OYYYYDDDDYYYYO.",
    "..OYYYYYYYYYYO..",
    "...OOYYYYYYOO...",
    "...OO......OO...",
    "................",
]

# 2. INIMIGOS DO ESCRITÓRIO (14x14 / 16x16)
# Padrão: Gabinete de Firma
GRID_INIMIGO_PADRAO = [
    "..OOOOOOOOOO..",
    ".OMSSSSSSSSMO.",
    ".OMZZZZZZZZMO.",
    ".OMZRRRRRRZMO.",
    ".OMZRWZZWRZMO.",
    ".OMZRRRRRRZMO.",
    ".OMZZZZZZZZMO.",
    ".OMMMMMMMMMMO.",
    ".OMZOOOOOOZMO.",
    ".OMMMMMMMMMMO.",
    ".OMZOOOOOOZMO.",
    "..OOMMMMMMOO..",
    "...OO....OO...",
    "...OO....OO...",
]

# Rápido: Mouse Óptico / Aspirador Turbo
GRID_INIMIGO_RAPIDO = [
    "....OOOOOO....",
    "..OOSSSSSSOO..",
    ".OSSMMMMMMSSO.",
    ".OSMRRRRRRMSO.",
    "OSMRRWWWWRRMSO",
    "OSMMMMMMMMMMSO",
    "OSMMMMNNMMMMSO",
    "OSMMMMNNMMMMSO",
    ".OSMMMMMMMMMSO",
    ".OOSSSSSSSSOO.",
    "...OO....OO...",
    "..OO......OO..",
]

# Tank: Copiadora Xerox / Servidor Rack
GRID_INIMIGO_TANK = [
    ".OOOOOOOOOOOOOO.",
    "OSSSSSSSSSSSSSSO",
    "OSZZZZZZZZZZZZSO",
    "OSZRRRRRRRRRRZSO",
    "OSZRWZZZZZZWRZSO",
    "OSZRRRRRRRRRRZSO",
    "OSMMMMMMMMMMMMSO",
    "OSMZOOOOOOOOZMSO",
    "OSMZZZZZZZZZZMSO",
    "OSMMMMMMMMMMMMSO",
    "OSMZUUUUUUUUZMSO",
    "OZZZZZZZZZZZZZZO",
    ".OOOMMMMMMMMOOO.",
    "..OOO......OOO..",
    "..OOO......OOO..",
    "................",
]

# Phasing: Monitor CRT / Sinal Fantasma
GRID_INIMIGO_PHASING = [
    "..OOOOOOOOOO..",
    ".OCCCCCCCCCCO.",
    "OCCKKKKKKKKCCO",
    "OCKAAACCCAAKCO",
    "OCKAWKCCCAWKCO",
    "OCKCCCCCCCCKCO",
    "OCKCAACACACKCO",
    "OCCKKKKKKKKCCO",
    ".OCCCCCCCCCCO.",
    "..OOCCCCCCOO..",
    "...OC.OO.CO...",
    "..OO..OO..OO..",
]

# Blindado: Triturador / Cofre Blindado
GRID_INIMIGO_BLINDADO = [
    ".OOOOOOOOOOOO.",
    "OZZZZZZZZZZZZO",
    "OZSSSSSSSSSSZO",
    "OZSZZZZZZZZSZO",
    "OZSZRRRRRRZSZO",
    "OZSZRWZZWRZSZO",
    "OZSZZZZZZZZSZO",
    "OZSSSSSSSSSSZO",
    "OZZZZUUUUZZZZO",
    "OZSSSSSSSSSSZO",
    "OZZZZZZZZZZZZO",
    ".OOZZZZZZZZOO.",
    "..OO......OO..",
    "..OO......OO..",
]

# Ranged (Nativo): Projetor Laser / Scanner Óptico
GRID_INIMIGO_RANGED = [
    "...OOOOOOOO...",
    "..OSSSSSSSSO..",
    ".OSZZZZZZZZSO.",
    "OSZMMMMMMMMZSO",
    "OSZMOOOOOOMZSO",
    "OSZMORRRRROMZO",
    "OSZMORWWWRROZO",
    "OSZMORRRRROMZO",
    "OSZMOOOOOOMZSO",
    ".OSZZZZZZZZSO.",
    "..OOOMMMMOOO..",
    "...OO.OO.OO...",
    "..OO..OO..OO..",
    "..............",
]

# 3. MINI-BOSSES DO ESCRITÓRIO (16x16 escalados para 56x56 / 64x64)
GRID_MINIBOSS_IMPRESSORA = [
    "..OOOOOOOOOOOO..",
    ".OWWWWWWWWWWWWo.".replace("o", "O"),
    ".OWKKKKKKKKKKWO.",
    "OOOOSSSSSSSSOOOO",
    "OSSSSSSSSSSSSSSO",
    "OSZZZZZZZZZZZZSO",
    "OSZRRRRRRRRRRZSO",
    "OSZRWWZZZZWWRZSO",
    "OSZRRRRRRRRRRZSO",
    "OSMMMMMMMMMMMMSO",
    "OSMZWWWWWWWWZMSO",
    "OSMZKKKKKKKKZMSO",
    "OZZZZZZZZZZZZZZO",
    ".OOOMMMMMMMMOOO.",
    "..OO........OO..",
    "..OO........OO..",
]

GRID_MINIBOSS_FONTE_500W = [
    ".OOOOOOOOOOOOOO.",
    "OZZZZZZZZZZZZZZO",
    "OZSNNNNNNNNNNSZO",
    "OZSNUUUUUUUUNSZO",
    "OZSNNNNNNNNNNSZO",
    "OZSMMMMMMMMMMSZO",
    "OZSMRRRRRRRRMSZO",
    "OZSMRWZZZZWRMSZO",
    "OZSMRRRRRRRRMSZO",
    "OZSMMMMMMMMMMSZO",
    "OZSMUUUUUUUUMSZO",
    "OZSNNNNNNNNNNSZO",
    "OZZZZZZZZZZZZZZO",
    ".OOONNNNNNNNOOO.",
    "..OOO......OOO..",
    "..OOO......OOO..",
]

GRID_MINIBOSS_ROTEADOR = [
    ".OO..........OO.",
    ".OCO........OCO.",
    ".OCO.OOOOOO.OCO.",
    ".OCOOCCCCCCOOcO.".replace("c", "C"),
    "..OCCCCCCCCCCO..",
    ".OCCKKKKKKKKCCO.",
    "OCCKAAACCCAAKCCO",
    "OCCKAWKCCCAWKCCO",
    "OCCKCCCCCCCCKCCO",
    "OCCKUUUUUUUUKCCO",
    ".OCCKKKKKKKKCCO.",
    "..OCCCCCCCCCCO..",
    "...OOCCCCCCOO...",
    "...OO..OO..OO...",
    "..OO...OO...OO..",
    "................",
]

GRID_MINIBOSS_NOBREAK = [
    "OOOOOOOOOOOOOOOO",
    "OSSSSSSSSSSSSSSO",
    "OSZZZZZZZZZZZZSO",
    "OSZUUUUUUUUUUZSO",
    "OSZRRRRRRRRRRZSO",
    "OSZRWZZZZZZWRZSO",
    "OSZRRRRRRRRRRZSO",
    "OSZZZZZZZZZZZZSO",
    "OSSSSSSSSSSSSSSO",
    "OSZCCCCCCCCCCZSO",
    "OSZCAACACACACZSO",
    "OSZZZZZZZZZZZZSO",
    "OSSSSSSSSSSSSSSO",
    "OOOOOOOOOOOOOOOO",
    "..OOOO....OOOO..",
    "..OOOO....OOOO..",
]

# Caixa de Som Destrutível da Geladeira Tsunami (14x14)
GRID_CAIXA_SOM = [
    ".OOOOOOOOOOOO.",
    "OZZZZZZZZZZZZO",
    "OZPPPPPPPPPPZO",
    "OZPOOOOOOOOOZO",
    "OZPOCCCCCCOOZO",
    "OZPOCUUUUCOOZO",
    "OZPOCUWWUCOOZO",
    "OZPOCUUUUCOOZO",
    "OZPOCCCCCCOOZO",
    "OZPOOOOOOOOOZO",
    "OZPPPPPPPPPPZO",
    "OZZZZZZZZZZZZO",
    ".OOZZZZZZZZOO.",
    "..............",
]

# 4. DRONES COMPANHEIROS (12x12)
GRID_DRONE_CURA = [
    "...OOOOOO...",
    "..OGGGGGGO..",
    ".OGGWWWWGGO.",
    "OGGWWGGWWGGO",
    "OGWWGGGGWWGO",
    "OGWGGGGGGWGO",
    "OGWGGGGGGWGO",
    "OGWWGGGGWWGO",
    "OGGWWGGWWGGO",
    ".OGGWWWWGGO.",
    "..OGGGGGGO..",
    "...OOOOOO...",
]

GRID_DRONE_COMBATE = [
    "...OOOOOO...",
    "..OSSSSSSO..",
    ".OSZZZZZZSO.",
    "OSZRRRRRRZSO",
    "OSZRWWWWWRZO",
    "OSZRWFFWRRZO",
    "OSZRWFFWRRZO",
    "OSZRWWWWWRZO",
    "OSZRRRRRRZSO",
    ".OSZZZZZZSO.",
    "..OSSSSSSO..",
    "...OOOOOO...",
]

GRID_DRONE_SUPORTE = [
    "...OOOOOO...",
    "..OCCCCCCO..",
    ".OCCAAAACCO.",
    "OCCAOOOOACCO",
    "OCAOCCCCOACO",
    "OCAOCWWCOACO",
    "OCAOCWWCOACO",
    "OCAOCCCCOACO",
    "OCCAOOOOACCO",
    ".OCCAAAACCO.",
    "..OCCCCCCO..",
    "...OOOOOO...",
]

# 5. DROPS & CÁPSULAS DE SUPRIMENTO (12x12 / 14x14)
GRID_DROP_XP = [
    "....OOOO....",
    "...OUUUUO...",
    "..OUUWWUUO..",
    ".OUUWWWWUUO.",
    "OUUWWUUUUUUO",
    "OUUUUUUUUUUO",
    "OUUUUUUUUUUO",
    "OUUUUUUNNUUO",
    ".OUUUUNNUUO.",
    "..OUUUUUUO..",
    "...OUUUUO...",
    "....OOOO....",
]

GRID_DROP_CURA = [
    "..OOOOOOOO..",
    ".OWWWWWWWWO.",
    "OWWWGGGGWWWO",
    "OWWWGGGGWWWO",
    "OWGGGGGGGGWO",
    "OWGGGGGGGGWO",
    "OWGGGGGGGGWO",
    "OWGGGGGGGGWO",
    "OWWWGGGGWWWO",
    "OWWWGGGGWWWO",
    ".OWWWWWWWWO.",
    "..OOOOOOOO..",
]

GRID_DROP_ARMA = [
    ".OOOOOOOOOO.",
    "OZZZZZZZZZZO",
    "OZUUUUUUUUZO",
    "OZUZZZZZZUZO",
    "OZUZNNNNZUZO",
    "OZUZNWWWNUZO",
    "OZUZNWWWNUZO",
    "OZUZNNNNZUZO",
    "OZUZZZZZZUZO",
    "OZUUUUUUUUZO",
    "OZZZZZZZZZZO",
    ".OOOOOOOOOO.",
]

GRID_DROP_EQUIP = [
    ".OOOOOOOOOO.",
    "OZZZZZZZZZZO",
    "OZCCCCCCCCZO",
    "OZCZZZZZZCZO",
    "OZCZAAAAZCZO",
    "OZCZA3WWACZO".replace("3", "W"),
    "OZCZA3WWACZO".replace("3", "W"),
    "OZCZAAAAZCZO",
    "OZCZZZZZZCZO",
    "OZCCCCCCCCZO",
    "OZZZZZZZZZZO",
    ".OOOOOOOOOO.",
]

GRID_DROP_OVERCLOCK = [
    "..OOOOOOOO..",
    ".OPPPPPPPPO.",
    "OPPLLLLLLPPO",
    "OPLOOOOOOLPO",
    "OPLOUUUUOLPO",
    "OPLOUWWUOLPO",
    "OPLOUWWUOLPO",
    "OPLOUUUUOLPO",
    "OPLOOOOOOLPO",
    "OPPLLLLLLPPO",
    ".OPPPPPPPPO.",
    "..OOOOOOOO..",
]

GRID_DROP_CAPSULA = [
    "...OOOOOO...",
    "..OCCCCCCO..",
    ".OCCWWWWCCO.",
    "OCCWCCCCWCCO",
    "OCWCCUUCCWCO",
    "OCWCUWWUCWCO",
    "OCWCUWWUCWCO",
    "OCWCCUUCCWCO",
    "OCCWCCCCWCCO",
    ".OCCWWWWCCO.",
    "..OCCCCCCO..",
    "...OOOOOO...",
]

_CACHE_SURFACES: dict[tuple, pygame.Surface] = {}


def _renderizar_grid(grid: list[str], largura_alvo: int, altura_alvo: int, tint: tuple = None) -> pygame.Surface:
    """Converte uma matriz de caracteres em uma pygame.Surface com escalonamento nearest-neighbor exato."""
    chave = (id(grid), int(largura_alvo), int(altura_alvo), tint)
    if chave in _CACHE_SURFACES:
        return _CACHE_SURFACES[chave]

    linhas = len(grid)
    colunas = max(len(r) for r in grid) if linhas > 0 else 1
    base = pygame.Surface((colunas, linhas), pygame.SRCALPHA)
    base.fill((0, 0, 0, 0))

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != "." and ch in PALETA_PIXEL:
                cor = PALETA_PIXEL[ch]
                if tint is not None and ch != "O":
                    cor = (
                        min(255, int(cor[0] * 0.6 + tint[0] * 0.4)),
                        min(255, int(cor[1] * 0.6 + tint[1] * 0.4)),
                        min(255, int(cor[2] * 0.6 + tint[2] * 0.4)),
                        255,
                    )
                base.set_at((x, y), cor)

    if (colunas, linhas) == (int(largura_alvo), int(altura_alvo)):
        final = base
    else:
        final = pygame.transform.scale(base, (max(1, int(largura_alvo)), max(1, int(altura_alvo))))

    _CACHE_SURFACES[chave] = final
    return final


def obter_sprite_batata(largura: int = 32, altura: int = 32, andando: bool = False, frame: int = 0) -> pygame.Surface:
    """Retorna o sprite em Pixel Art Limpo do Cleiton (Batata)."""
    grid = GRID_BATATA_WALK if (andando and frame % 2 == 1) else GRID_BATATA_IDLE
    return _renderizar_grid(grid, largura, altura)


def obter_sprite_inimigo(
    sprite_key: str,
    largura: int = 28,
    altura: int = 28,
    is_elite: bool = False,
    arquetipo_miniboss: str = ""
) -> pygame.Surface:
    """
    Retorna o sprite em Pixel Art Limpo para inimigos comuns, Mini-Bosses e Caixas de Som.
    Retorna None para 'boss_geladeira_tsunami' para que a Geladeira use sempre seu PNG original.
    """
    if sprite_key == "boss_geladeira_tsunami":
        return None

    if sprite_key == "caixa_som_boss" or arquetipo_miniboss == "caixa_som_boss":
        return _renderizar_grid(GRID_CAIXA_SOM, largura, altura)

    if is_elite:
        mapa_mini = {
            "impressora_matricial": GRID_MINIBOSS_IMPRESSORA,
            "fonte_generica": GRID_MINIBOSS_FONTE_500W,
            "roteador_corporativo": GRID_MINIBOSS_ROTEADOR,
            "nobreak_chumbado": GRID_MINIBOSS_NOBREAK,
        }
        if arquetipo_miniboss in mapa_mini:
            return _renderizar_grid(mapa_mini[arquetipo_miniboss], largura, altura)
        if "rapido" in sprite_key:
            return _renderizar_grid(GRID_MINIBOSS_IMPRESSORA, largura, altura)
        if "tank" in sprite_key:
            return _renderizar_grid(GRID_MINIBOSS_FONTE_500W, largura, altura)
        if "phasing" in sprite_key:
            return _renderizar_grid(GRID_MINIBOSS_ROTEADOR, largura, altura)
        if "blindado" in sprite_key:
            return _renderizar_grid(GRID_MINIBOSS_NOBREAK, largura, altura)

    mapa_comuns = {
        "inimigo_padrao": GRID_INIMIGO_PADRAO,
        "inimigo_rapido": GRID_INIMIGO_RAPIDO,
        "inimigo_tank": GRID_INIMIGO_TANK,
        "inimigo_phasing": GRID_INIMIGO_PHASING,
        "inimigo_blindado": GRID_INIMIGO_BLINDADO,
        "inimigo_ranged": GRID_INIMIGO_RANGED,
        "inimigo_impressora": GRID_MINIBOSS_IMPRESSORA,
        "inimigo_ninja": [
            ".....OOOOOO.....",
            "...OOKKKKKKOO...",
            "..OKKPPPPPPKKO..",
            "..OKOOOOOOOOOKO.",
            "..OKOCOCCCCCOCK.",
            "..OKOOOOOOOOOKO.",
            "...OOKKKKKKOO...",
            "..OKKLPKKPLKKO..",
            ".OKKLPKKKKPLKKO.",
            ".OCKKKKKKKKKKKO.",
            ".OCCKKKKKKKKKKO.",
            "..O.OKKKKKKO.O..",
            "....OOOOOOOO....",
            "....OKK..KKO....",
            "....OKK..KKO....",
            "....OOO..OOO....",
        ],
        "cubo_criogenico": GRID_INIMIGO_BLINDADO,
    }
    grid = mapa_comuns.get(sprite_key, GRID_INIMIGO_PADRAO)
    return _renderizar_grid(grid, largura, altura)


def obter_sprite_drone(sprite_key: str, largura: int = 24, altura: int = 24, nivel_mk: int = 1) -> pygame.Surface:
    """Retorna o sprite em Pixel Art Limpo para os 3 tipos de Drones com detalhes por nível MK."""
    chave = ("drone", sprite_key, int(largura), int(altura), int(nivel_mk))
    if chave in _CACHE_SURFACES:
        return _CACHE_SURFACES[chave]

    if "cura" in sprite_key:
        grid = GRID_DRONE_CURA
        cor_mk = (74, 222, 128)
    elif "suporte" in sprite_key:
        grid = GRID_DRONE_SUPORTE
        cor_mk = (56, 189, 248)
    else:
        grid = GRID_DRONE_COMBATE
        cor_mk = (250, 204, 21)

    base = _renderizar_grid(grid, largura, altura).copy()
    if nivel_mk >= 2:
        pygame.draw.rect(base, cor_mk, (0, 0, largura, altura), width=1, border_radius=3)
    if nivel_mk >= 3:
        pygame.draw.rect(base, (255, 215, 0), (1, 1, largura - 2, altura - 2), width=1, border_radius=2)

    _CACHE_SURFACES[chave] = base
    return base


def obter_sprite_drop(tipo: str, largura: int = 20, altura: int = 20) -> pygame.Surface:
    """Retorna o sprite em Pixel Art Limpo para gemas de XP, kits de cura, caixas, overclocks e cápsulas."""
    mapa = {
        "xp": GRID_DROP_XP,
        "cura": GRID_DROP_CURA,
        "arma": GRID_DROP_ARMA,
        "equipamento": GRID_DROP_EQUIP,
        "config": GRID_DROP_OVERCLOCK,
        "overclock": GRID_DROP_OVERCLOCK,
        "capsula_powerup": GRID_DROP_CAPSULA,
    }
    grid = mapa.get(tipo, GRID_DROP_XP)
    return _renderizar_grid(grid, largura, altura)
