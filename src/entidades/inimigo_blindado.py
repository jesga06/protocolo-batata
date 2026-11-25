import math
import pygame
from src.entidades.inimigo_base import InimigoBase
from src.utils.constantes import (
    INIMIGO_BLINDADO_HP, INIMIGO_BLINDADO_VELOCIDADE,
    INIMIGO_BLINDADO_DANO, INIMIGO_BLINDADO_COOLDOWN_ATAQUE,
    INIMIGO_BLINDADO_XP, INIMIGO_BLINDADO_VEL_GIRO,
    INIMIGO_BLINDADO_CARGAS, INIMIGO_BLINDADO_REGEN_MINIBOSS,
    LARGURA_TELA, ALTURA_TELA,
)
from src.utils.math_utils import vetor_direcao, normalizar_vetor
from src.utils.pixel_art_sprites import obter_sprite_inimigo
from src.utils.traducao import t


class InimigoBlindado(InimigoBase):
    nome_exibicao = t("combate_entidades", "inim_blindado")
    """
    Inimigo com couraça protetora reforçada, controles de tanque e placa balística frontal.
    - Gira lentamente em direção ao alvo e desloca-se sempre na direção frontal (facing).
    - Redução de 30% de dano para impactos frontais (cone de 90°) enquanto a placa estiver íntegra.
    - Ataques pelas costas ou flancos causam 100% de dano total sem gastar a placa.
    - Explosões, ataques melee e disparos sobrecarregados pela frente quebram a placa após 2 golpes.
    - O Mini-Boss (elite) regenera a placa após 10s sem receber novo ataque frontal que a quebraria.
    """

    _rot_cache: dict[tuple, pygame.Surface] = {}
    _elite_placa_cache: dict[tuple, pygame.Surface] = {}

    def __init__(
        self,
        x: float,
        y: float,
        hp: int = INIMIGO_BLINDADO_HP,
        velocidade: float = INIMIGO_BLINDADO_VELOCIDADE,
        dano_contato: int = INIMIGO_BLINDADO_DANO,
        cooldown_contato: float = INIMIGO_BLINDADO_COOLDOWN_ATAQUE,
        xp_valor: int = INIMIGO_BLINDADO_XP,
        reducao_frontal: float = 0.30,
        arco_frontal_graus: float = 90.0,
        is_elite: bool = False,
        nome_elite: str = "",
        vel_giro_rad_s: float = INIMIGO_BLINDADO_VEL_GIRO,
        cargas_blindagem: int = INIMIGO_BLINDADO_CARGAS,
        tempo_regen_blindagem: float = INIMIGO_BLINDADO_REGEN_MINIBOSS,
    ):
        super().__init__(
            x=x,
            y=y,
            hp=hp,
            velocidade=velocidade,
            dano_contato=dano_contato,
            cooldown_contato=cooldown_contato,
            xp_valor=xp_valor,
            score_valor=250,
            largura=47,
            altura=47,
            sprite_key="inimigo_blindado",
            is_elite=is_elite,
            nome_elite=nome_elite
        )

        self.reducao_frontal = float(reducao_frontal)
        self.arco_frontal_graus = float(arco_frontal_graus)
        self.vel_giro_rad_s = max(0.05, float(vel_giro_rad_s))
        self.cargas_blindagem_max = max(1, int(cargas_blindagem))
        self.cargas_blindagem = self.cargas_blindagem_max
        self.blindagem_quebrada = False
        self.regenera_blindagem = bool(is_elite)
        self.tempo_regen_blindagem = max(0.1, float(tempo_regen_blindagem))
        self.timer_regen_blindagem = 0.0
        self.eventos_blindagem_pendentes: list[dict] = []

        # Vetor unitário de orientação (olhando para a direita por padrão)
        self.facing_x = 1.0
        self.facing_y = 0.0

    def orientar_para(self, tx: float, ty: float) -> None:
        """Orienta instantaneamente o chassi na direção de (tx, ty) (usado no spawn)."""
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        ux, uy = vetor_direcao(cx, cy, float(tx), float(ty))
        if ux != 0.0 or uy != 0.0:
            self.facing_x = ux
            self.facing_y = uy

    def _obter_direcao_movimento(
        self, cx: float, cy: float, tx: float, ty: float
    ) -> tuple[float, float]:
        """Controles de tanque: desloca-se sempre reto na direção frontal atual."""
        return (self.facing_x, self.facing_y)

    def update(self, dt: float, pos_alvo: tuple[float, float]):
        """Gira lentamente em direção ao alvo, atualiza regeneração (elite) e anda para frente."""
        if not self.vivo:
            return

        dt = float(dt)
        if self.regenera_blindagem and self.blindagem_quebrada:
            self.timer_regen_blindagem -= dt
            if self.timer_regen_blindagem <= 0.0:
                self.timer_regen_blindagem = 0.0
                self.blindagem_quebrada = False
                self.cargas_blindagem = self.cargas_blindagem_max
                self.eventos_blindagem_pendentes.append({
                    "tipo": "regenerada",
                    "x": self.x + self.largura / 2.0,
                    "y": self.y + self.altura / 2.0,
                    "dir_x": self.facing_x,
                    "dir_y": self.facing_y,
                })

        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0
        tx, ty = getattr(self, "pos_alvo_override", None) or pos_alvo

        ux, uy = vetor_direcao(cx, cy, tx, ty)
        if ux != 0.0 or uy != 0.0:
            ang_atual = math.atan2(self.facing_y, self.facing_x)
            ang_alvo = math.atan2(uy, ux)
            delta = (ang_alvo - ang_atual + math.pi) % (2.0 * math.pi) - math.pi
            max_passo = self.vel_giro_rad_s * dt
            if abs(delta) <= max_passo:
                ang_novo = ang_alvo
            else:
                ang_novo = ang_atual + math.copysign(max_passo, delta)
            self.facing_x = math.cos(ang_novo)
            self.facing_y = math.sin(ang_novo)

        super().update(dt, pos_alvo)

    def is_ataque_frontal(
        self,
        origem_x: float = None,
        origem_y: float = None,
        dir_ataque: tuple[float, float] = None
    ) -> bool:
        """
        Determina se um ataque incide dentro do arco frontal de 90° (+-45° do vetor de visão).
        Retorna True se o impacto veio pela frente.
        """
        meio_arco_rad = math.radians(self.arco_frontal_graus / 2.0)
        cos_limite = math.cos(meio_arco_rad)

        if origem_x is not None and origem_y is not None:
            cx = self.x + self.largura / 2.0
            cy = self.y + self.altura / 2.0
            vox, voy = vetor_direcao(cx, cy, float(origem_x), float(origem_y))
            dot = self.facing_x * vox + self.facing_y * voy
            return dot >= cos_limite

        if dir_ataque is not None:
            adx, ady = normalizar_vetor(dir_ataque[0], dir_ataque[1])
            dot = -(self.facing_x * adx + self.facing_y * ady)
            return dot >= cos_limite

        return False

    def receber_dano(
        self,
        quantidade: int,
        origem_x: float = None,
        origem_y: float = None,
        dir_ataque: tuple[float, float] = None,
        *args,
        **kwargs
    ) -> int:
        """
        Calcula atenuação da armadura frontal e quebra após 2 ataques frontais válidos
        (explosões, melee ou disparos sobrecarregados).
        """
        if not self.vivo or int(quantidade) <= 0:
            return 0

        if dir_ataque is None and "dir_ataque" in kwargs:
            dir_ataque = kwargs["dir_ataque"]
        if origem_x is None and "origem_x" in kwargs:
            origem_x = kwargs["origem_x"]
        if origem_y is None and "origem_y" in kwargs:
            origem_y = kwargs["origem_y"]

        dano_base = int(quantidade)
        ignorar_blindagem = bool(kwargs.get("ignorar_blindagem", False))
        quebra_blindagem = bool(kwargs.pop("quebra_blindagem", False))

        frontal = self.is_ataque_frontal(origem_x=origem_x, origem_y=origem_y, dir_ataque=dir_ataque)
        cx = self.x + self.largura / 2.0
        cy = self.y + self.altura / 2.0

        if self.blindagem_quebrada:
            if frontal and quebra_blindagem and self.regenera_blindagem:
                self.timer_regen_blindagem = self.tempo_regen_blindagem
            kwargs["ignorar_blindagem"] = True
            return super().receber_dano(dano_base, *args, **kwargs)

        if not ignorar_blindagem and frontal:
            dano_efetivo = max(1, int(round(dano_base * (1.0 - self.reducao_frontal))))
            if quebra_blindagem:
                self.cargas_blindagem = max(0, self.cargas_blindagem - 1)
                if self.cargas_blindagem <= 0:
                    self.blindagem_quebrada = True
                    if self.regenera_blindagem:
                        self.timer_regen_blindagem = self.tempo_regen_blindagem
                    self.eventos_blindagem_pendentes.append({
                        "tipo": "quebra",
                        "x": cx + self.facing_x * (self.largura * 0.42),
                        "y": cy + self.facing_y * (self.altura * 0.42),
                        "dir_x": self.facing_x,
                        "dir_y": self.facing_y,
                    })
                else:
                    self.eventos_blindagem_pendentes.append({
                        "tipo": "rachadura",
                        "x": cx + self.facing_x * (self.largura * 0.42),
                        "y": cy + self.facing_y * (self.altura * 0.42),
                        "dir_x": self.facing_x,
                        "dir_y": self.facing_y,
                    })
        else:
            dano_efetivo = dano_base

        return super().receber_dano(dano_efetivo, *args, **kwargs)

    @classmethod
    def _obter_sprite_elite_com_placa(
        cls, base_surf: pygame.Surface, largura: int, altura: int
    ) -> pygame.Surface:
        chave = (id(base_surf), largura, altura)
        cached = cls._elite_placa_cache.get(chave)
        if cached is not None:
            return cached
        if len(cls._elite_placa_cache) >= 32:
            cls._elite_placa_cache.clear()
        surf = base_surf.copy()
        w, h = surf.get_size()
        barra_w = max(5, w // 7)
        bx = max(0, w - barra_w)
        pygame.draw.rect(surf, (20, 24, 32, 255), (bx, 2, barra_w, max(4, h - 4)))
        if barra_w >= 4 and h >= 8:
            pygame.draw.rect(surf, (226, 232, 240, 255), (bx + 1, 3, barra_w - 2, h - 6))
        cls._elite_placa_cache[chave] = surf
        return surf

    @classmethod
    def _obter_sprite_rotacionado(
        cls, base_surf: pygame.Surface, ang_graus: float, flash: bool
    ) -> pygame.Surface:
        ang_q = round(float(ang_graus) / 3.0) * 3.0
        chave = (id(base_surf), ang_q, bool(flash))
        cached = cls._rot_cache.get(chave)
        if cached is not None:
            return cached
        if len(cls._rot_cache) >= 512:
            cls._rot_cache.clear()
        surf = base_surf
        if flash:
            surf = surf.copy()
            surf.fill((255, 200, 200, 200), special_flags=pygame.BLEND_ADD)
        if abs(ang_q) > 0.5:
            surf = pygame.transform.rotate(surf, ang_q)
        cls._rot_cache[chave] = surf
        return surf

    def desenhar(self, janela, camera=None):
        """Renderiza o Triturador Blindado rotacionado para facing_x/facing_y com placa intacta ou quebrada."""
        if not self.vivo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        largura_tela = getattr(janela, "largura", LARGURA_TELA)
        altura_tela = getattr(janela, "altura", ALTURA_TELA)
        margem = max(80, self.largura, self.altura)
        if draw_x < -margem or draw_x > largura_tela + margem or draw_y < -margem or draw_y > altura_tela + margem:
            return

        screen = getattr(janela, "screen", janela)

        if getattr(janela, "low_graphics", False):
            cor = (255, 255, 255) if self.flash_timer > 0.0 else self._obter_cor_low_graphics()
            ix, iy = int(draw_x), int(draw_y)
            w, h = self.largura, self.altura
            pygame.draw.rect(screen, cor, (ix, iy, w, h))
            pygame.draw.rect(screen, (20, 24, 32), (ix, iy, w, h), width=2)
            if not self.blindagem_quebrada:
                cx_i = draw_x + w / 2.0
                cy_i = draw_y + h / 2.0
                px_perp = -self.facing_y
                py_perp = self.facing_x
                fx = cx_i + self.facing_x * (w * 0.48)
                fy = cy_i + self.facing_y * (h * 0.48)
                meio = h * 0.46
                p1 = (int(round(fx + px_perp * meio)), int(round(fy + py_perp * meio)))
                p2 = (int(round(fx - px_perp * meio)), int(round(fy - py_perp * meio)))
                pygame.draw.line(screen, (226, 232, 240), p1, p2, width=4)
            if getattr(self, "is_elite", False):
                pygame.draw.rect(screen, (255, 215, 0), (ix - 2, iy - 2, w + 4, h + 4), width=2)
            return

        offset_bob = int(abs(math.sin(self.anim_timer * 8.0)) * 3.0)
        draw_y -= offset_bob

        display_inited = pygame.display.get_init()
        if getattr(self, "is_elite", False):
            try:
                ticks = pygame.time.get_ticks() if display_inited else 0
                pulso = math.sin(ticks / 150.0) * 4.0
                raio_aura = max(self.largura, self.altura) / 2.0 + 8.0 + pulso
                centro_x = int(draw_x + self.largura / 2.0)
                centro_y = int(draw_y + self.altura / 2.0)
                dim_aura = max(10, int((raio_aura + 4.0) * 2))
                if display_inited and dim_aura in self._aura_cache:
                    aura_surf = self._aura_cache[dim_aura]
                else:
                    aura_surf = pygame.Surface((dim_aura, dim_aura), pygame.SRCALPHA)
                    aura_cx = dim_aura // 2
                    aura_cy = dim_aura // 2
                    raio_desenho = max(1, int(raio_aura))
                    pygame.draw.circle(aura_surf, (175, 75, 255, 90), (aura_cx, aura_cy), raio_desenho)
                    pygame.draw.circle(aura_surf, (255, 215, 0, 180), (aura_cx, aura_cy), raio_desenho, width=2)
                    if display_inited:
                        self._aura_cache[dim_aura] = aura_surf
                screen.blit(aura_surf, (centro_x - dim_aura // 2, centro_y - dim_aura // 2))
            except (pygame.error, OSError, ImportError):
                pass

        sprite = None
        if getattr(self, "is_elite", False):
            try:
                sprite = obter_sprite_inimigo(
                    self.sprite_key,
                    self.largura,
                    self.altura,
                    self.is_elite,
                    getattr(self, "arquetipo_miniboss", ""),
                )
            except (pygame.error, OSError, KeyError):
                sprite = None
            if sprite is not None:
                cache_key = (self.sprite_key, self.largura, self.altura)
                if cache_key not in self._sprite_cache:
                    self._sprite_cache[cache_key] = pygame.transform.scale(sprite, (self.largura, self.altura))
                sprite = self._sprite_cache[cache_key]
                if not self.blindagem_quebrada:
                    sprite = self._obter_sprite_elite_com_placa(sprite, self.largura, self.altura)
        else:
            chave_sprite = "inimigo_blindado_sem_escudo" if self.blindagem_quebrada else self.sprite_key
            sprite = self._obter_sprite(chave_sprite)
            if sprite is None and self.blindagem_quebrada:
                sprite = self._obter_sprite(self.sprite_key)

        if sprite is not None:
            ang_graus = -math.degrees(math.atan2(self.facing_y, self.facing_x))
            sprite_rot = self._obter_sprite_rotacionado(sprite, ang_graus, self.flash_timer > 0.0)
            rw, rh = sprite_rot.get_width(), sprite_rot.get_height()
            blit_x = int(round(draw_x + self.largura / 2.0 - rw / 2.0))
            blit_y = int(round(draw_y + self.altura / 2.0 - rh / 2.0))
            screen.blit(sprite_rot, (blit_x, blit_y))
        else:
            cor = (255, 255, 255) if self.flash_timer > 0.0 else (80, 110, 150)
            pygame.draw.rect(
                screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura),
            )


