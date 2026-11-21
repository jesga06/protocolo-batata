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
    JOGADOR_INVULNERABILIDADE_TEMPO,
    obter_caminho_asset, VERDE_CURA, VERMELHO_HP
)
from src.utils.math_utils import normalizar_vetor, clamp


class Jogador:
    """
    Representa o avatar da Batata controlada pelo jogador.
    """
    _sprite_idle = None
    _sprite_dano = None
    _sprite_flip_cache = {}
    _flash_cache = {}
    _ghost_surf_cache = {}
    _aura_cache = {}

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
        self.mult_dano_config = 1.0

        self.buff_dano_timer = 0.0
        self.buff_vel_timer = 0.0
        self.buff_cadencia_timer = 0.0
        self.buff_resistencia_timer = 0.0
        self.escudo_ativo = False
        self.escudo_sobrevida = 0
        self.evento_cura_drone = 0
        self.anim_timer = 0.0
        self.andando_frame = False
        self.abates_overvolt_contador = 0
        self.timer_sem_atirar_refrig = 0.0
        self.pulso_frio_pronto = False
        self.coprocessador_escudo_timer = 0.0

        self.vivo = True
        self.ultima_causa_morte = ""
        self.vx_knockback = 0.0
        self.vy_knockback = 0.0
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
        self.coprocessadores_angulos = [0.0, 3.14159]
        self.refrigeracao_nitrogenio = False
        self.refrigeracao_carga = 0.0
        self.refrigeracao_overdrive_timer = 0.0
        self.overvolt = False
        self.bios_modding = False
        self.slot_especial_secundario_ativo = False
        self.protecao_surtos = False
        self.escudo_fatal_pronto = False
        self.escudo_fatal_invuln_timer = 0.0
        self.escudo_fatal_cooldown = 0.0
        self.kernel_panic_trigger = False
        self.upgrade_barramento = False
        self.fila_disparos_echo = []

        # Fix 5.2: fps_stutter_dodge & motion_blur_ghosting
        self.fps_stutter_dodge = False
        self.stutter_freeze_timer = 0.0
        self.motion_blur_ghosting = False
        self.rastro_posicoes = []
        self._rastro_timer = 0.0

        # Fix 5.3: keybinds_overdrive_dash & mira uma_mao
        self.keybinds_overdrive_dash = False
        self.overdrive_dash_cooldown = 0.0
        self.overdrive_pulse_trigger = False
        self._ult_dir_x = 0.0
        self._ult_dir_y = 0.0
        self.ultima_dir_dx = 0.0
        self.ultima_dir_dy = -1.0
        self.dir_movimento = (0.0, -1.0)

    def aplicar_knockback(self, dir_x: float, dir_y: float, forca: float):
        """Aplica impulso suave de repulsão (ex: Rocket-Jump, Bass Push) decaindo ao longo dos frames."""
        self.vx_knockback += float(dir_x) * float(forca)
        self.vy_knockback += float(dir_y) * float(forca)

    def aplicar_pulso_magnetico(self, drops: list):
        """Puxa instantaneamente os drops ativos na arena (exceto cápsulas de escolha) para a Batata."""
        if not drops:
            return
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        for drop in drops:
            if getattr(drop, "tipo", "") == "capsula_powerup":
                continue
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
        """
        Adiciona um novo drone ao enxame ou evolui (MK-I -> MK-II -> MK-III) um drone ativo do mesmo tipo,
        mantendo no máximo 3 unidades físicas orbitando a Batata (1 de cada classe).
        """
        if novo_drone is not None:
            import math
            for d in self.drones:
                if getattr(d, "ativo", False) and type(d) is type(novo_drone):
                    if hasattr(d, "evoluir_mk"):
                        d.evoluir_mk()
                    d.tempo_vida = max(float(getattr(d, "tempo_vida", 30.0)), float(getattr(novo_drone, "tempo_vida", 30.0)))
                    d.tempo_restante = d.tempo_vida
                    return
            if self.drones:
                novo_drone.angulo_orbita = (self.drones[-1].angulo_orbita + (2.0 * math.pi / 3.0)) % (2.0 * math.pi)
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
        overclocks_conhecidos = {
            "multithreading",
            "refrigeracao",
            "overvolt",
            "bios_modding",
            "protecao_surtos",
            "upgrade_barramento",
        }
        if mod_id not in overclocks_conhecidos or mod_id in self.overclocks_adquiridos:
            return

        self.overclocks_adquiridos.add(mod_id)

        if mod_id == "multithreading":
            self.multithreading = True
            self.coprocessadores_angulos = [0.0, 3.14159]
        elif mod_id == "refrigeracao":
            self.refrigeracao_nitrogenio = True
            self.refrigeracao_carga = 0.0
            self.refrigeracao_overdrive_timer = 0.0
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

    def equipar_arma_especial(self, nova_arma):
        """
        Equipa uma arma especial nos slots do jogador com escalonamento de dano imediato
        e suporte a Dual-Wield de BIOS Modding.
        """
        if nova_arma is None:
            return

        if not hasattr(nova_arma, "_dano_original"):
            nova_arma._dano_original = nova_arma.dano
        nova_arma.dano = int(round(nova_arma._dano_original * getattr(self, "mult_dano_config", 1.0)))

        if not getattr(self, "bios_modding", False) or self.arma_especial is None:
            nova_arma.slot = 3
            self.arma_especial = nova_arma
            self.slot_ativo = 3
            self.slot_especial_secundario_ativo = False
        else:
            nova_arma.slot = 2
            if len(self.armas) > 1:
                self.armas[1] = nova_arma
            else:
                self.armas.append(nova_arma)
            self.arma_especial_secundaria = nova_arma
            self.slot_ativo = 2
            self.slot_especial_secundario_ativo = False

    def selecionar_slot(self, slot: int):
        """Alterna a arma ativa para o slot 1, 2 ou 3. Se BIOS Modding ativo e já no Slot 3, alterna entre 3A e 3B."""
        if slot == 3:
            from src.armas.pistola import Pistola
            if (
                getattr(self, "bios_modding", False)
                and self.arma_especial_secundaria is not None
                and len(self.armas) > 1
                and not isinstance(self.armas[1], Pistola)
                and self.arma_especial is not None
            ):
                self.arma_especial, self.armas[1] = self.armas[1], self.arma_especial
                self.arma_especial.slot = 3
                self.armas[1].slot = 2
                self.arma_especial_secundaria = self.armas[1]
                self.slot_ativo = 3
                self.slot_especial_secundario_ativo = not getattr(self, "slot_especial_secundario_ativo", False)
            elif self.slot_ativo == 3 and getattr(self, "bios_modding", False):
                self.slot_especial_secundario_ativo = not getattr(self, "slot_especial_secundario_ativo", False)
                if self.arma_especial_secundaria is not None:
                    # Alterna as duas armas especiais
                    self.arma_especial, self.arma_especial_secundaria = self.arma_especial_secundaria, self.arma_especial
                self.slot_ativo = 3
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

        if mov_mouse and preset_teclas != "uma_mao" and mouse is not None:
            try:
                import math
                mx, my = mouse.get_position()
                if camera is not None and hasattr(camera, "obter_mouse_mundo"):
                    mx, my = camera.obter_mouse_mundo(mx, my)
                elif camera is not None:
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

        # Fix 5.3: keybinds_overdrive_dash (direction-reversal dash impulse & shockwave trigger)
        self.dir_movimento_atual = (dx, dy)
        if dx != 0.0 or dy != 0.0:
            self.ultima_dir_dx = dx
            self.ultima_dir_dy = dy
            self.dir_movimento = (dx, dy)
            if getattr(self, "keybinds_overdrive_dash", False) and getattr(self, "overdrive_dash_cooldown", 0.0) <= 0.0:
                ult_x = getattr(self, "_ult_dir_x", 0.0)
                ult_y = getattr(self, "_ult_dir_y", 0.0)
                if (ult_x != 0.0 or ult_y != 0.0) and (dx * ult_x + dy * ult_y) < -0.35:
                    self.x += dx * 32.0
                    self.y += dy * 32.0
                    self.overdrive_dash_cooldown = 2.5
                    self.overdrive_pulse_trigger = True
                    if getattr(self, "motion_blur_ghosting", False):
                        self.invulnerabilidade_timer = max(self.invulnerabilidade_timer, 0.40)
            self._ult_dir_x, self._ult_dir_y = dx, dy
        else:
            # No modo uma_mao (100% teclado), dispara para cima (0.0, -1.0) quando parado
            self.dir_movimento = (0.0, -1.0)

        # Atualiza posição com velocidade por segundo
        self.andando_frame = (dx != 0.0 or dy != 0.0)
        if self.andando_frame:
            self.anim_timer += dt
        self.x += dx * self.velocidade_atual * dt
        self.y += dy * self.velocidade_atual * dt

        # Boundary clamping estrito dentro dos limites da arena
        max_x = max(0.0, float(limite_arena[0]) - self.largura)
        max_y = max(0.0, float(limite_arena[1]) - self.altura)
        self.x = clamp(self.x, 0.0, max_x)
        self.y = clamp(self.y, 0.0, max_y)

        # Orientação visual (facing) baseado na posição virtual do mouse ou na direção
        if preset_teclas == "uma_mao":
            if dx < 0:
                self.facing_right = False
            elif dx > 0:
                self.facing_right = True
        elif mouse is not None:
            try:
                mx, _ = mouse.get_position()
                if camera is not None and hasattr(camera, "obter_mouse_mundo"):
                    mx, _ = camera.obter_mouse_mundo(mx, 0.0)
                elif camera is not None:
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

    def receber_dano(self, quantidade: int, causa_morte: str = ""):
        """Aplica dano ao jogador, aciona flash visual, registra causa da morte e testa condição de morte."""
        if not self.vivo or getattr(self, "modo_deus", False) or getattr(self, "invulneravel", False):
            return

        if int(quantidade) <= 0:
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
            dano_a_aplicar = max(1, int(round(dano_a_aplicar * 0.92)))

        # Barreira de Sobrevida (Drone de Cura quando vida cheia)
        if getattr(self, "escudo_sobrevida", 0) > 0:
            absorvido = min(self.escudo_sobrevida, dano_a_aplicar)
            self.escudo_sobrevida -= absorvido
            dano_a_aplicar -= absorvido
            if dano_a_aplicar <= 0:
                self.flash_dano_timer = JOGADOR_COOLDOWN_DANO_FLASH
                self.invulnerabilidade_timer = max(self.invulnerabilidade_timer, float(JOGADOR_INVULNERABILIDADE_TEMPO))
                return True

        # Proteção contra Surtos (Escudo Fatal: mitiga dano letal, 4s invuln + recupera 50% HP + 60s cooldown pós-invuln)
        if dano_a_aplicar >= self.hp and getattr(self, "protecao_surtos", False) and getattr(self, "escudo_fatal_pronto", False):
            self.escudo_fatal_pronto = False
            self.escudo_fatal_invuln_timer = 4.0
            self.invulnerabilidade_timer = 4.0
            self.flash_dano_timer = JOGADOR_COOLDOWN_DANO_FLASH
            self.hp = max(1, self.hp_max // 2)
            self.kernel_panic_trigger = True
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
            self.ultima_causa_morte = causa_morte or "Dano fatal no escritório"
            try:
                from PPlay.sound import Sound
                sfx = Sound(obter_caminho_asset("sfx_morte_jogador"))
                sfx.play()
            except Exception:
                pass
        else:
            invuln_base = float(JOGADOR_INVULNERABILIDADE_TEMPO)
            if getattr(self, "fps_stutter_dodge", False):
                self.stutter_freeze_timer = 0.12
                invuln_base += 0.35
            if getattr(self, "motion_blur_ghosting", False):
                invuln_base += 0.40
            self.invulnerabilidade_timer = max(self.invulnerabilidade_timer, invuln_base)
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
        """Retorna lista de dicionários com informações de todos os buffs ativos para o HUD."""
        ativos = []
        if self.buff_dano_timer > 0.0:
            ativos.append({
                "id": "dano",
                "nome": "DANO +5%",
                "timer": self.buff_dano_timer,
                "duracao": 15.0,
                "cor": (255, 90, 90),
                "cor_bg": (60, 20, 20)
            })
        if self.buff_cadencia_timer > 0.0:
            ativos.append({
                "id": "cadencia",
                "nome": "CADÊNCIA +8%",
                "timer": self.buff_cadencia_timer,
                "duracao": 15.0,
                "cor": (220, 110, 255),
                "cor_bg": (50, 15, 60)
            })
        if self.buff_vel_timer > 0.0:
            ativos.append({
                "id": "velocidade",
                "nome": "VEL +8%",
                "timer": self.buff_vel_timer,
                "duracao": 15.0,
                "cor": (255, 220, 70),
                "cor_bg": (55, 45, 15)
            })
        if self.buff_resistencia_timer > 0.0:
            ativos.append({
                "id": "resistencia",
                "nome": "DEFESA -8%",
                "timer": self.buff_resistencia_timer,
                "duracao": 15.0,
                "cor": (80, 220, 120),
                "cor_bg": (15, 50, 25)
            })
        if getattr(self, "escudo_ativo", False):
            ativos.append({
                "id": "escudo",
                "nome": "ESCUDO ATIVO",
                "timer": 999.0,
                "duracao": 999.0,
                "cor": (100, 220, 255),
                "cor_bg": (20, 45, 65)
            })
        if self.invulnerabilidade_timer > 0.0:
            ativos.append({
                "id": "invulnerabilidade",
                "nome": f"INVULN {self.invulnerabilidade_timer:.1f}s",
                "timer": self.invulnerabilidade_timer,
                "duracao": 4.0,
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
                    "duracao": 4.0,
                    "cor": (255, 215, 0),
                    "cor_bg": (60, 50, 10)
                })
            else:
                ativos.append({
                    "id": "surto",
                    "nome": f"SURTO {self.escudo_fatal_cooldown:.0f}s",
                    "timer": self.escudo_fatal_cooldown,
                    "duracao": 60.0,
                    "cor": (180, 180, 200),
                    "cor_bg": (40, 40, 50)
                })
        if getattr(self, "refrigeracao_nitrogenio", False):
            if getattr(self, "refrigeracao_overdrive_timer", 0.0) > 0.0:
                ativos.append({
                    "id": "refrigeracao_overdrive",
                    "nome": f"OVERDRIVE {self.refrigeracao_overdrive_timer:.1f}s",
                    "timer": self.refrigeracao_overdrive_timer,
                    "duracao": 6.0,
                    "cor": (0, 255, 255),
                    "cor_bg": (10, 45, 60)
                })
            else:
                carga_pct = int(round(getattr(self, "refrigeracao_carga", 0.0) * 100))
                ativos.append({
                    "id": "refrigeracao",
                    "nome": f"NITRO {carga_pct}%",
                    "timer": self.refrigeracao_carga,
                    "duracao": 1.0,
                    "cor": (140, 220, 255),
                    "cor_bg": (15, 35, 55)
                })
        return ativos

    def update(self, dt: float, drops: list = None, inimigos: list = None):
        """Atualiza timers de flash de dano, knockback suave, armas, buffs temporários e drone companheiro."""
        if abs(self.vx_knockback) > 1.0 or abs(self.vy_knockback) > 1.0:
            self.x += self.vx_knockback * dt
            self.y += self.vy_knockback * dt
            fator_decay = 0.85 ** (dt * 60.0)
            self.vx_knockback *= fator_decay
            self.vy_knockback *= fator_decay
        else:
            self.vx_knockback = 0.0
            self.vy_knockback = 0.0

        if self.flash_dano_timer > 0.0:
            self.flash_dano_timer = max(0.0, self.flash_dano_timer - dt)

        if self.invulnerabilidade_timer > 0.0:
            self.invulnerabilidade_timer = max(0.0, self.invulnerabilidade_timer - dt)

        if getattr(self, "stutter_freeze_timer", 0.0) > 0.0:
            self.stutter_freeze_timer = max(0.0, self.stutter_freeze_timer - dt)

        if getattr(self, "overdrive_dash_cooldown", 0.0) > 0.0:
            self.overdrive_dash_cooldown = max(0.0, self.overdrive_dash_cooldown - dt)

        if getattr(self, "motion_blur_ghosting", False):
            self._rastro_timer = getattr(self, "_rastro_timer", 0.0) + dt
            if self._rastro_timer >= 0.03:
                self._rastro_timer = 0.0
                if not hasattr(self, "rastro_posicoes"):
                    self.rastro_posicoes = []
                self.rastro_posicoes.append((self.x, self.y, self.facing_right))
                if len(self.rastro_posicoes) > 5:
                    self.rastro_posicoes.pop(0)
        else:
            if getattr(self, "rastro_posicoes", None):
                self.rastro_posicoes.clear()
            self._rastro_timer = 0.0

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
                self.escudo_fatal_cooldown = 60.0
        elif getattr(self, "escudo_fatal_cooldown", 0.0) > 0.0:
            self.escudo_fatal_cooldown = max(0.0, self.escudo_fatal_cooldown - dt)
            if self.escudo_fatal_cooldown == 0.0:
                self.escudo_fatal_pronto = True

        # Multithreading: atualiza ângulos de rotação dos 2 coprocessadores
        if getattr(self, "multithreading", False):
            if not hasattr(self, "coprocessadores_angulos"):
                self.coprocessadores_angulos = [0.0, 3.14159]
            self.coprocessadores_angulos[0] = (self.coprocessadores_angulos[0] + 2.5 * dt) % (2.0 * 3.14159265)
            self.coprocessadores_angulos[1] = (self.coprocessadores_angulos[1] + 2.5 * dt) % (2.0 * 3.14159265)

        # Refrigeração a Nitrogênio: +20% cadência base e onda de frio após 1.5s sem atirar
        mult_refrigeracao = 1.0
        if getattr(self, "refrigeracao_nitrogenio", False):
            mult_refrigeracao = 1.20
            self.timer_sem_atirar_refrig = getattr(self, "timer_sem_atirar_refrig", 0.0) + dt
            if self.timer_sem_atirar_refrig >= 1.5:
                self.timer_sem_atirar_refrig = 0.0
                self.pulso_frio_pronto = True

        mult_cadencia = mult_refrigeracao * (1.08 if self.buff_cadencia_timer > 0.0 else 1.0)
        dt_armas = dt * mult_cadencia

        for arma in self.armas:
            arma.update(dt_armas)

        # Fallback de Munição no Slot 2 para Pistola padrão
        if len(self.armas) > 1:
            arma_slot_2 = self.armas[1]
            from src.armas.pistola import Pistola
            if not isinstance(arma_slot_2, Pistola) and getattr(arma_slot_2, "municao_atual", 1) <= 0:
                p = Pistola()
                p._dano_original = p.dano
                p.dano = int(round(p._dano_original * getattr(self, "mult_dano_config", 1.0)))
                self.armas[1] = p
                self.arma_especial_secundaria = None

        if self.arma_especial is not None:
            self.arma_especial.update(dt_armas)
            # Regra de Esgotamento de Munição (Slot 3 Lifecycle)
            if self.arma_especial.municao_atual <= 0:
                if (
                    getattr(self, "bios_modding", False)
                    and getattr(self, "arma_especial_secundaria", None) is not None
                    and self.arma_especial_secundaria != self.arma_especial
                ):
                    self.arma_especial = self.arma_especial_secundaria
                    self.arma_especial.slot = 3
                    from src.armas.pistola import Pistola
                    if len(self.armas) > 1 and not isinstance(self.armas[1], Pistola):
                        p = Pistola()
                        p._dano_original = p.dano
                        p.dano = int(round(p._dano_original * getattr(self, "mult_dano_config", 1.0)))
                        self.armas[1] = p
                    self.arma_especial_secundaria = None
                    self.slot_especial_secundario_ativo = False
                else:
                    self.arma_especial = None
                    self.slot_especial_secundario_ativo = False
                    if self.slot_ativo == 3:
                        self.slot_ativo = 2

        if getattr(self, "arma_especial_secundaria", None) is not None:
            if self.arma_especial_secundaria != self.arma_especial and self.arma_especial_secundaria != (self.armas[1] if len(self.armas) > 1 else None):
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
        self.recalcular_velocidade()

        return novos_projeteis_drone

    def recalcular_velocidade(self, mult_vel_config: float = None):
        """
        Recalcula a velocidade atual do jogador considerando modificadores de config,
        buffs temporários (1.08), upgrade de barramento (1.40) e drones de suporte (teto de 2.0x).
        """
        if mult_vel_config is not None:
            self.mult_vel_config = float(mult_vel_config)

        mult_vel_suporte = 1.0
        from src.equipamentos.drone_suporte import DroneSuporte
        for d in self.drones:
            if getattr(d, "ativo", False) and getattr(d, "tempo_restante", 0.0) > 0.0 and getattr(d, "hp", 0) > 0:
                if isinstance(d, DroneSuporte):
                    mult_vel_suporte *= (1.0 + getattr(d, "bonus_velocidade", 0.15))

        # Teto seguro para multiplicador de suporte (máx 2.0x)
        mult_vel_suporte = min(2.0, mult_vel_suporte)

        mult_buff_vel = 1.08 if getattr(self, "buff_vel_timer", 0.0) > 0.0 else 1.0
        mult_barramento = 1.15 if getattr(self, "upgrade_barramento", False) else 1.0
        mult_config = getattr(self, "mult_vel_config", 1.0)

        self.velocidade_atual = self.velocidade_base * mult_vel_suporte * mult_config * mult_buff_vel * mult_barramento

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna caixa delimitadora (x, y, w, h)."""
        return (self.x, self.y, self.largura, self.altura)

    def desenhar(self, janela, camera=None):
        """Renderiza o avatar da batata e seus drones ativos com suporte a câmera, efeito de dano e modo low_graphics."""
        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y
        screen = getattr(janela, "screen", janela)
        is_low_graphics = getattr(janela, "low_graphics", False)

        if not is_low_graphics:
            try:
                from src.utils.pixel_art_sprites import obter_sprite_batata
                frame_idx = int(getattr(self, "anim_timer", 0.0) * 8.0)
                sprite_base = obter_sprite_batata(
                    self.largura,
                    self.altura,
                    andando=getattr(self, "andando_frame", False),
                    frame=frame_idx
                )
            except Exception:
                self._carregar_sprites()
                sprite_base = self._sprite_dano if (self.flash_dano_timer > 0.0 and self._sprite_dano) else self._sprite_idle
        else:
            sprite_base = None

        import math
        offset_bob = int(round(abs(math.sin(getattr(self, "anim_timer", 0.0) * 10.0)) * 3.0)) if getattr(self, "andando_frame", False) else 0
        draw_y_bob = draw_y - offset_bob

        display_inited = pygame.display.get_init()

        # Efeito de Afterimage / Ghosting para Motion Blur (Config 6)
        if getattr(self, "motion_blur_ghosting", False) and getattr(self, "rastro_posicoes", None):
            for i, (rx, ry, r_facing) in enumerate(self.rastro_posicoes):
                rdx = camera.transform_x(rx) if camera else rx
                rdy = camera.transform_y(ry) if camera else ry
                alpha = int(40 + (i + 1) * (90 / max(1, len(self.rastro_posicoes))))
                if sprite_base is not None and not is_low_graphics:
                    sw, sh = sprite_base.get_width(), sprite_base.get_height()
                    blit_rx = int(rdx + (self.largura - sw) // 2)
                    blit_ry = int(rdy + (self.altura - sh) // 2)
                    if display_inited:
                        tipo_sprite = "dano" if (self.flash_dano_timer > 0.0 and self._sprite_dano) else "idle"
                        cache_key = (tipo_sprite, bool(r_facing), alpha)
                        if cache_key not in self._ghost_surf_cache:
                            base_flip = sprite_base if r_facing else pygame.transform.flip(sprite_base, True, False)
                            ghost_surf = base_flip.copy()
                            ghost_surf.set_alpha(alpha)
                            self._ghost_surf_cache[cache_key] = ghost_surf
                        else:
                            ghost_surf = self._ghost_surf_cache[cache_key]
                        screen.blit(ghost_surf, (blit_rx, blit_ry))
                    else:
                        ghost_surf = pygame.transform.flip(sprite_base, True, False) if not r_facing else sprite_base.copy()
                        ghost_surf.set_alpha(alpha)
                        screen.blit(ghost_surf, (blit_rx, blit_ry))
                else:
                    if display_inited:
                        cache_key = ("fallback_ghost", self.largura, self.altura, alpha)
                        if cache_key not in self._ghost_surf_cache:
                            ghost_surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
                            ghost_surf.fill((190, 150, 90, alpha))
                            self._ghost_surf_cache[cache_key] = ghost_surf
                        else:
                            ghost_surf = self._ghost_surf_cache[cache_key]
                        screen.blit(ghost_surf, (int(rdx), int(rdy)))
                    else:
                        ghost_surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
                        ghost_surf.fill((190, 150, 90, alpha))
                        screen.blit(ghost_surf, (int(rdx), int(rdy)))

        if is_low_graphics:
            cor = (255, 80, 80) if self.flash_dano_timer > 0.0 else (210, 165, 85)
            ix, iy = int(draw_x), int(draw_y)
            pygame.draw.rect(screen, cor, (ix, iy, self.largura, self.altura), border_radius=6)
            pygame.draw.rect(screen, (80, 50, 20), (ix, iy, self.largura, self.altura), width=2, border_radius=6)
            olho_x = ix + self.largura - 8 if self.facing_right else ix + 6
            olho_y = iy + 8
            pygame.draw.circle(screen, (30, 30, 30), (olho_x, olho_y), 3)
        elif sprite_base is not None:
            # Sombra pixelada sob os pés da Batata
            pygame.draw.ellipse(
                screen,
                (10, 12, 18),
                (int(draw_x + 4), int(draw_y + self.altura - 5), max(8, self.largura - 8), 6)
            )
            sw, sh = sprite_base.get_width(), sprite_base.get_height()
            blit_x = int(draw_x + (self.largura - sw) // 2)
            blit_y = int(draw_y_bob + (self.altura - sh) // 2)

            surface_to_draw = sprite_base if self.facing_right else pygame.transform.flip(sprite_base, True, False)
            if self.flash_dano_timer > 0.0:
                flash_s = surface_to_draw.copy()
                flash_s.fill((255, 90, 90, 0), special_flags=pygame.BLEND_RGBA_ADD)
                surface_to_draw = flash_s

            screen.blit(surface_to_draw, (blit_x, blit_y))

            # Anel hexagonal de Casco Eletrostático (buff_resistencia_timer > 0)
            if getattr(self, "buff_resistencia_timer", 0.0) > 0.0:
                cx_e = draw_x + self.largura / 2.0
                cy_e = draw_y_bob + self.altura / 2.0
                pts_hex = [
                    (int(cx_e + math.cos(i * math.pi / 3.0) * 22), int(cy_e + math.sin(i * math.pi / 3.0) * 22))
                    for i in range(6)
                ]
                pygame.draw.polygon(screen, (80, 220, 120), pts_hex, width=1)
        else:
            # Fallback visual
            cor = (255, 80, 80) if self.flash_dano_timer > 0.0 else (190, 150, 90)
            pygame.draw.rect(
                screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura),
                border_radius=8
            )

        # Multithreading: renderiza 2 mini-coprocessadores orbitais
        if getattr(self, "multithreading", False):
            import math
            cx = draw_x + self.largura / 2.0
            cy = draw_y + self.altura / 2.0
            raio_orbita = 34.0
            for ang in getattr(self, "coprocessadores_angulos", [0.0, 3.14159]):
                px = cx + math.cos(ang) * raio_orbita
                py = cy + math.sin(ang) * raio_orbita
                pygame.draw.circle(screen, (0, 240, 255), (int(px), int(py)), 5)
                pygame.draw.circle(screen, (255, 255, 255), (int(px), int(py)), 2)

        # Renderiza todos os drones ativos no enxame
        for d in self.drones:
            if getattr(d, "ativo", False):
                d.desenhar(janela, camera)
