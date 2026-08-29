"""
Entidade do Jogador (Batata) — Protocolo: Batata
Controla o avatar principal do jogo, movimento com normalização diagonal,
mira virtual, recebimento de dano, inventário de armas e renderização.
"""

import os
import pygame
from src.utils.constantes import (
    JOGADOR_HP_MAX_PADRAO, JOGADOR_VELOCIDADE_PADRAO,
    JOGADOR_LARGURA, JOGADOR_ALTURA, JOGADOR_COOLDOWN_DANO_FLASH,
    obter_caminho_asset, VERDE_CURA, VERMELHO_HP
)
from src.utils.math_utils import normalizar_vetor, clamp


class Jogador:
    """
    Representa o avatar da Batata controlada pelo jogador.
    """
    _sprite_idle = None
    _sprite_dano = None

    def __init__(
        self,
        x: float,
        y: float,
        hp_max: int = JOGADOR_HP_MAX_PADRAO,
        velocidade: float = JOGADOR_VELOCIDADE_PADRAO
    ):
        self.x = float(x)
        self.y = float(y)
        self.largura = int(JOGADOR_LARGURA)
        self.altura = int(JOGADOR_ALTURA)
        self.width = self.largura
        self.height = self.altura

        self.hp_max = int(hp_max)
        self.hp = int(hp_max)
        self.velocidade_base = float(velocidade)
        self.velocidade_atual = float(velocidade)
        self.mult_vel_config = 1.0

        self.buff_dano_timer = 0.0
        self.buff_vel_timer = 0.0
        self.buff_cadencia_timer = 0.0
        self.buff_resistencia_timer = 0.0
        self.escudo_ativo = False

        self.vivo = True
        self.facing_right = True
        self.flash_dano_timer = 0.0
        self.invulnerabilidade_timer = 0.0

        # Inventário de armas inicial (Slot 1: Melee, Slot 2: Pistola, Slot 3: Especial)
        from src.armas.melee import Melee
        from src.armas.pistola import Pistola
        from src.sistemas.sistema_xp import SistemaXP
        self.armas = [Melee(), Pistola()]
        self.arma_especial = None
        self.arma_especial_secundaria = None
        self.drones = []
        self.slot_ativo = 2  # Padrão: Slot 2 (Pistola)
        self.sistema_xp = SistemaXP()

        # Módulos de Overclock BIOS
        self.overclocks_adquiridos = set()
        self.multithreading = False
        self.refrigeracao_nitrogenio = False
        self.overvolt = False
        self.bios_modding = False
        self.slot_especial_secundario_ativo = False
        self.protecao_surtos = False
        self.escudo_fatal_pronto = False
        self.escudo_fatal_invuln_timer = 0.0
        self.escudo_fatal_cooldown = 0.0
        self.upgrade_barramento = False
        self.fila_disparos_echo = []

    def aplicar_pulso_magnetico(self, drops: list):
        """Puxa instantaneamente todos os drops ativos na arena diretamente para a coordenada da Batata."""
        if not drops:
            return
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        for drop in drops:
            if getattr(drop, "ativo", False) and not getattr(drop, "coletado", False):
                drop.x = cx - getattr(drop, "largura", 16) / 2.0
                drop.y = cy - getattr(drop, "altura", 16) / 2.0

    @property
    def drone(self):
        return self.drones[0] if self.drones else None

    @drone.setter
    def drone(self, val):
        if val is None:
            self.drones.clear()
        else:
            self.drones = [val]

    def adicionar_drone(self, novo_drone):
        """Adiciona um novo drone ao enxame com defasagem angular para não colidir visualmente."""
        if novo_drone is not None:
            import math
            if self.drones:
                novo_drone.angulo_orbita = (self.drones[-1].angulo_orbita + math.pi / 2.0) % (2.0 * math.pi)
            self.drones.append(novo_drone)

    @property
    def xp(self) -> int:
        return self.sistema_xp.xp_atual

    @xp.setter
    def xp(self, valor: int):
        self.sistema_xp.xp_atual = int(valor)

    @property
    def nivel(self) -> int:
        return self.sistema_xp.nivel

    @nivel.setter
    def nivel(self, valor: int):
        self.sistema_xp.nivel = int(valor)

    @property
    def xp_proximo(self) -> int:
        return self.sistema_xp.xp_para_proximo_nivel()

    def ganhar_xp(self, quantidade: int, mult_xp: float = 1.0) -> list[int]:
        """Adiciona XP ao jogador e retorna lista de níveis subidos."""
        return self.sistema_xp.adicionar_xp(quantidade, mult_xp)

    def aplicar_overclock(self, mod_id: str):
        """Aplica os efeitos permanentes do módulo de Overclock à Batata."""
        if not mod_id:
            return
        self.overclocks_adquiridos.add(mod_id)

        if mod_id == "multithreading":
            self.multithreading = True
        elif mod_id == "refrigeracao":
            self.refrigeracao_nitrogenio = True
        elif mod_id == "overvolt":
            self.overvolt = True
        elif mod_id == "bios_modding":
            self.bios_modding = True
        elif mod_id == "protecao_surtos":
            self.protecao_surtos = True
            self.hp_max += 50
            self.hp = min(self.hp_max, self.hp + 50)
            self.escudo_fatal_pronto = True
            self.escudo_fatal_invuln_timer = 0.0
            self.escudo_fatal_cooldown = 0.0
        elif mod_id == "upgrade_barramento":
            self.upgrade_barramento = True

    def selecionar_slot(self, slot: int):
        """Alterna a arma ativa para o slot 1, 2 ou 3. Se BIOS Modding ativo e já no Slot 3, alterna entre 3A e 3B."""
        if slot == 3:
            if self.slot_ativo == 3 and getattr(self, "bios_modding", False):
                self.slot_especial_secundario_ativo = not getattr(self, "slot_especial_secundario_ativo", False)
                if self.arma_especial_secundaria is not None:
                    # Alterna as duas armas especiais
                    self.arma_especial, self.arma_especial_secundaria = self.arma_especial_secundaria, self.arma_especial
            else:
                self.slot_especial_secundario_ativo = False
            self.slot_ativo = 3
        elif slot in (1, 2):
            self.slot_ativo = slot
            self.slot_especial_secundario_ativo = False

    def obter_arma_ativa(self):
        """Retorna a instância da arma correspondente ao slot_ativo atual."""
        if self.slot_ativo == 1:
            for arma in self.armas:
                if getattr(arma, "slot", None) == 1:
                    return arma
            return self.armas[0] if self.armas else None
        elif self.slot_ativo == 2:
            for arma in self.armas:
                if getattr(arma, "slot", None) == 2:
                    return arma
            return self.armas[1] if len(self.armas) > 1 else (self.armas[0] if self.armas else None)
        elif self.slot_ativo == 3:
            return self.arma_especial
        return None

    @classmethod
    def _carregar_sprites(cls):
        if cls._sprite_idle is None:
            try:
                caminho_idle = obter_caminho_asset("jogador_idle")
                if os.path.isfile(caminho_idle):
                    cls._sprite_idle = pygame.image.load(caminho_idle).convert_alpha()
            except Exception:
                cls._sprite_idle = None

        if cls._sprite_dano is None:
            try:
                caminho_dano = obter_caminho_asset("jogador_dano")
                if os.path.isfile(caminho_dano):
                    cls._sprite_dano = pygame.image.load(caminho_dano).convert_alpha()
            except Exception:
                cls._sprite_dano = None

    def processar_input(
        self,
        teclado,
        mouse,
        dt: float,
        config_sistema=None,
        limite_arena: tuple[float, float] = (1600.0, 1200.0),
        camera=None
    ):
        """
        Processa teclas de movimento (WASD, Setas, Presets ou Autopilot Mouse), seleção de armas (1, 2, 3),
        normaliza movimento diagonal e restringe o jogador aos limites da arena.
        """
        if not self.vivo:
            return

        dx = 0.0
        dy = 0.0

        # Verifica modo de movimento pelo mouse (Config 10) e Presets de teclas (Config 11)
        mov_mouse = False
        preset_teclas = "padrao"
        if config_sistema is not None:
            if hasattr(config_sistema, "obter_valor"):
                mov_mouse = (config_sistema.obter_valor("movimento_mouse") in (True, "Ligado", "ligado", "1"))
                preset_teclas = str(config_sistema.obter_valor("keybinds")).lower()
            elif isinstance(config_sistema, dict):
                mov_mouse = (config_sistema.get("movimento_mouse") in (True, "Ligado", "ligado", "1"))
                preset_teclas = str(config_sistema.get("keybinds", "padrao")).lower()

        if teclado is not None:
            # Troca de armas via teclas numéricas 1, 2 e 3
            if hasattr(teclado, "key_down") and teclado.key_down("1"):
                self.selecionar_slot(1)
            elif hasattr(teclado, "key_down") and teclado.key_down("2"):
                self.selecionar_slot(2)
            elif hasattr(teclado, "key_down") and teclado.key_down("3"):
                self.selecionar_slot(3)

        if mov_mouse and mouse is not None:
            try:
                import math
                mx, my = mouse.get_position()
                if camera is not None:
                    mx += camera.x
                    my += camera.y
                cx = self.x + self.largura / 2.0
                cy = self.y + self.altura / 2.0
                dist_mouse = math.hypot(mx - cx, my - cy)
                if dist_mouse > 8.0:
                    dx = (mx - cx) / dist_mouse
                    dy = (my - cy) / dist_mouse
            except Exception:
                pass
        elif teclado is not None:
            if preset_teclas == "invertido":
                if teclado.key_pressed("a") or teclado.key_pressed("left") or teclado.key_pressed("LEFT"):
                    dx += 1.0
                if teclado.key_pressed("d") or teclado.key_pressed("right") or teclado.key_pressed("RIGHT"):
                    dx -= 1.0
                if teclado.key_pressed("w") or teclado.key_pressed("up") or teclado.key_pressed("UP"):
                    dy += 1.0
                if teclado.key_pressed("s") or teclado.key_pressed("down") or teclado.key_pressed("DOWN"):
                    dy -= 1.0
            elif preset_teclas == "arrow_keys":
                if teclado.key_pressed("left") or teclado.key_pressed("LEFT"):
                    dx -= 1.0
                if teclado.key_pressed("right") or teclado.key_pressed("RIGHT"):
                    dx += 1.0
                if teclado.key_pressed("up") or teclado.key_pressed("UP"):
                    dy -= 1.0
                if teclado.key_pressed("down") or teclado.key_pressed("DOWN"):
                    dy += 1.0
            elif preset_teclas == "uma_mao":
                # QWER: Q (esquerda), W (cima), E (baixo), R (direita)
                if teclado.key_pressed("q") or teclado.key_pressed("Q"):
                    dx -= 1.0
                if teclado.key_pressed("r") or teclado.key_pressed("R"):
                    dx += 1.0
                if teclado.key_pressed("w") or teclado.key_pressed("W"):
                    dy -= 1.0
                if teclado.key_pressed("e") or teclado.key_pressed("E"):
                    dy += 1.0
            elif preset_teclas == "pesadelo":
                # IJKL: J (esquerda), L (direita), I (cima), K (baixo)
                if teclado.key_pressed("j") or teclado.key_pressed("J"):
                    dx -= 1.0
                if teclado.key_pressed("l") or teclado.key_pressed("L"):
                    dx += 1.0
                if teclado.key_pressed("i") or teclado.key_pressed("I"):
                    dy -= 1.0
                if teclado.key_pressed("k") or teclado.key_pressed("K"):
                    dy += 1.0
            else:
                # Padrão WASD + Setas
                if teclado.key_pressed("a") or teclado.key_pressed("left") or teclado.key_pressed("LEFT"):
                    dx -= 1.0
                if teclado.key_pressed("d") or teclado.key_pressed("right") or teclado.key_pressed("RIGHT"):
                    dx += 1.0
                if teclado.key_pressed("w") or teclado.key_pressed("up") or teclado.key_pressed("UP"):
                    dy -= 1.0
                if teclado.key_pressed("s") or teclado.key_pressed("down") or teclado.key_pressed("DOWN"):
                    dy += 1.0

        # Normalização diagonal exata (dx, dy * 0.7071 ou vetor unitário)
        if not mov_mouse and dx != 0.0 and dy != 0.0:
            dx *= 0.70710678118
            dy *= 0.70710678118

        # Atualiza posição com velocidade por segundo
        self.x += dx * self.velocidade_atual * dt
        self.y += dy * self.velocidade_atual * dt

        # Boundary clamping estrito dentro dos limites da arena
        max_x = max(0.0, float(limite_arena[0]) - self.largura)
        max_y = max(0.0, float(limite_arena[1]) - self.altura)
        self.x = clamp(self.x, 0.0, max_x)
        self.y = clamp(self.y, 0.0, max_y)

        # Orientação visual (facing) baseado na posição virtual do mouse ou na direção
        if mouse is not None:
            try:
                mx, _ = mouse.get_position()
                if camera is not None:
                    mx += camera.x
                # Se mouse estiver à esquerda do centro do jogador, vira para a esquerda
                if mx < self.x + self.largura / 2.0:
                    self.facing_right = False
                else:
                    self.facing_right = True
            except Exception:
                if dx < 0:
                    self.facing_right = False
                elif dx > 0:
                    self.facing_right = True
        else:
            if dx < 0:
                self.facing_right = False
            elif dx > 0:
                self.facing_right = True

    def receber_dano(self, quantidade: int):
        """Aplica dano ao jogador, aciona flash visual e testa condição de morte."""
        if not self.vivo or getattr(self, "modo_deus", False) or getattr(self, "invulneravel", False):
            return

        if self.invulnerabilidade_timer > 0.0:
            return

        if self.escudo_ativo:
            self.escudo_ativo = False
            self.invulnerabilidade_timer = 4.0
            self.flash_dano_timer = JOGADOR_COOLDOWN_DANO_FLASH
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_dano_jogador"))
                sfx.play()
            except Exception:
                pass
            return

        dano_a_aplicar = int(quantidade)
        if self.buff_resistencia_timer > 0.0:
            dano_a_aplicar = max(1, int(round(dano_a_aplicar * 0.85)))

        # Proteção contra Surtos (Escudo Fatal: mitiga dano letal, 5s invuln + 45s cooldown pós-invuln)
        if dano_a_aplicar >= self.hp and getattr(self, "protecao_surtos", False) and getattr(self, "escudo_fatal_pronto", False):
            self.escudo_fatal_pronto = False
            self.escudo_fatal_invuln_timer = 5.0
            self.invulnerabilidade_timer = 5.0
            self.flash_dano_timer = JOGADOR_COOLDOWN_DANO_FLASH
            self.hp = 1
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_dano_jogador"))
                sfx.play()
            except Exception:
                pass
            return

        self.hp = max(0, self.hp - dano_a_aplicar)
        self.flash_dano_timer = JOGADOR_COOLDOWN_DANO_FLASH

        if self.hp <= 0:
            self.vivo = False
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_morte_jogador"))
                sfx.play()
            except Exception:
                pass
        else:
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_dano_jogador"))
                sfx.play()
            except Exception:
                pass

    def curar(self, quantidade: int):
        """Restaura HP do jogador até o teto de hp_max."""
        if not self.vivo:
            return
        self.hp = min(self.hp_max, self.hp + int(quantidade))

    def obter_buffs_ativos(self) -> list[dict]:
        """Retorna lista de buffs e escudos ativos no jogador para exibição no HUD."""
        ativos = []
        if self.buff_dano_timer > 0.0:
            ativos.append({
                "id": "dano",
                "nome": "DANO +20%",
                "timer": self.buff_dano_timer,
                "duracao": 15.0,
                "cor": (255, 100, 80),
                "cor_bg": (60, 20, 20)
            })
        if self.buff_cadencia_timer > 0.0:
            ativos.append({
                "id": "cadencia",
                "nome": "TIRO +30%",
                "timer": self.buff_cadencia_timer,
                "duracao": 15.0,
                "cor": (220, 110, 255),
                "cor_bg": (50, 15, 60)
            })
        if self.buff_vel_timer > 0.0:
            ativos.append({
                "id": "velocidade",
                "nome": "VEL +12%",
                "timer": self.buff_vel_timer,
                "duracao": 15.0,
                "cor": (255, 220, 70),
                "cor_bg": (55, 45, 15)
            })
        if self.buff_resistencia_timer > 0.0:
            ativos.append({
                "id": "resistencia",
                "nome": "DEFESA -15%",
                "timer": self.buff_resistencia_timer,
                "duracao": 15.0,
                "cor": (80, 220, 120),
                "cor_bg": (15, 50, 25)
            })
        if getattr(self, "escudo_ativo", False) or self.invulnerabilidade_timer > 0.0:
            ativos.append({
                "id": "escudo",
                "nome": "ESCUDO ATIVO" if getattr(self, "escudo_ativo", False) else f"INVULN {self.invulnerabilidade_timer:.1f}s",
                "timer": self.invulnerabilidade_timer if self.invulnerabilidade_timer > 0.0 else 999.0,
                "duracao": 4.0 if self.invulnerabilidade_timer > 0.0 else 999.0,
                "cor": (100, 220, 255),
                "cor_bg": (20, 45, 65)
            })
        if getattr(self, "protecao_surtos", False):
            if getattr(self, "escudo_fatal_pronto", False):
                ativos.append({
                    "id": "surto",
                    "nome": "DISJUNTOR PRONTO",
                    "timer": 999.0,
                    "duracao": 999.0,
                    "cor": (140, 255, 160),
                    "cor_bg": (20, 60, 30)
                })
            elif getattr(self, "escudo_fatal_invuln_timer", 0.0) > 0.0:
                ativos.append({
                    "id": "surto",
                    "nome": f"SURTO INVULN {self.escudo_fatal_invuln_timer:.1f}s",
                    "timer": self.escudo_fatal_invuln_timer,
                    "duracao": 5.0,
                    "cor": (255, 215, 0),
                    "cor_bg": (60, 50, 10)
                })
            else:
                ativos.append({
                    "id": "surto",
                    "nome": f"SURTO {self.escudo_fatal_cooldown:.0f}s",
                    "timer": self.escudo_fatal_cooldown,
                    "duracao": 45.0,
                    "cor": (180, 180, 200),
                    "cor_bg": (40, 40, 50)
                })
        return ativos

    def update(self, dt: float, drops: list = None, inimigos: list = None):
        """Atualiza timers de flash de dano, armas, buffs temporários e drone companheiro."""
        if self.flash_dano_timer > 0.0:
            self.flash_dano_timer = max(0.0, self.flash_dano_timer - dt)

        if self.invulnerabilidade_timer > 0.0:
            self.invulnerabilidade_timer = max(0.0, self.invulnerabilidade_timer - dt)

        if self.buff_dano_timer > 0.0:
            self.buff_dano_timer = max(0.0, self.buff_dano_timer - dt)

        if self.buff_vel_timer > 0.0:
            self.buff_vel_timer = max(0.0, self.buff_vel_timer - dt)

        if self.buff_cadencia_timer > 0.0:
            self.buff_cadencia_timer = max(0.0, self.buff_cadencia_timer - dt)

        if self.buff_resistencia_timer > 0.0:
            self.buff_resistencia_timer = max(0.0, self.buff_resistencia_timer - dt)

        # Atualiza timer do escudo fatal de Proteção contra Surtos
        if getattr(self, "escudo_fatal_invuln_timer", 0.0) > 0.0:
            self.escudo_fatal_invuln_timer = max(0.0, self.escudo_fatal_invuln_timer - dt)
            if self.escudo_fatal_invuln_timer == 0.0:
                self.escudo_fatal_cooldown = 45.0
        elif getattr(self, "escudo_fatal_cooldown", 0.0) > 0.0:
            self.escudo_fatal_cooldown = max(0.0, self.escudo_fatal_cooldown - dt)
            if self.escudo_fatal_cooldown == 0.0:
                self.escudo_fatal_pronto = True

        mult_cadencia = (1.35 if getattr(self, "refrigeracao_nitrogenio", False) else 1.0) * (1.30 if self.buff_cadencia_timer > 0.0 else 1.0)
        dt_armas = dt * mult_cadencia

        for arma in self.armas:
            arma.update(dt_armas)

        if self.arma_especial is not None:
            self.arma_especial.update(dt_armas)
            # Regra de Esgotamento de Munição (Slot 3 Lifecycle)
            if self.arma_especial.municao_atual <= 0:
                if getattr(self, "bios_modding", False) and self.arma_especial_secundaria is not None:
                    self.arma_especial = self.arma_especial_secundaria
                    self.arma_especial_secundaria = None
                else:
                    self.arma_especial = None
                    if self.slot_ativo == 3:
                        self.slot_ativo = 2

        if getattr(self, "arma_especial_secundaria", None) is not None:
            self.arma_especial_secundaria.update(dt_armas)
            if self.arma_especial_secundaria.municao_atual <= 0:
                self.arma_especial_secundaria = None

        # Atualização dos Drones Companheiros (Slot 4 - Múltiplos Drones Simultâneos)
        novos_projeteis_drone = []
        drones_vivos = []
        mult_vel_suporte = 1.0

        for d in self.drones:
            if not getattr(d, "ativo", False) or getattr(d, "tempo_restante", 0.0) <= 0.0 or getattr(d, "hp", 0) <= 0:
                continue
            drones_vivos.append(d)

            # Aplica bônus cumulativo de velocidade de drones de suporte
            from src.equipamentos.drone_suporte import DroneSuporte
            if isinstance(d, DroneSuporte):
                mult_vel_suporte *= (1.0 + getattr(d, "bonus_velocidade", 0.15))

            res = d.update(dt, jogador=self, drops=drops, inimigos=inimigos)
            if isinstance(res, list):
                novos_projeteis_drone.extend(res)

        self.drones = drones_vivos
        mult_buff_vel = 1.12 if self.buff_vel_timer > 0.0 else 1.0
        mult_barramento = 1.40 if getattr(self, "upgrade_barramento", False) else 1.0
        mult_config = getattr(self, "mult_vel_config", 1.0)
        self.velocidade_atual = self.velocidade_base * mult_vel_suporte * mult_config * mult_buff_vel * mult_barramento

        return novos_projeteis_drone

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna caixa delimitadora (x, y, w, h)."""
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o avatar da batata e seus drones ativos com suporte a câmera e efeito de dano."""
        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        self._carregar_sprites()

        # Seleciona sprite apropriado (idle ou dano)
        sprite_base = self._sprite_dano if (self.flash_dano_timer > 0.0 and self._sprite_dano) else self._sprite_idle

        if sprite_base is not None:
            # Se virado para a esquerda, inverte horizontalmente
            surface_to_draw = sprite_base
            if not self.facing_right:
                surface_to_draw = pygame.transform.flip(sprite_base, True, False)
            janela.screen.blit(surface_to_draw, (int(draw_x), int(draw_y)))
        else:
            # Fallback visual
            cor = (255, 80, 80) if self.flash_dano_timer > 0.0 else (190, 150, 90)
            pygame.draw.rect(
                janela.screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura),
                border_radius=8
            )

        # Renderiza todos os drones ativos no enxame
        for d in self.drones:
            if getattr(d, "ativo", False):
                d.desenhar(janela, camera)
