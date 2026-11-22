"""
Entidade de Projétil — Protocolo: Batata
Controla a física, tempo de vida, renderização e colisões de tiros no jogo.
"""

import math
import os
import pygame
from src.utils.constantes import ASSETS_DIR, ASSET_PATHS, obter_caminho_asset, AMARELO_XP, LARANJA_ALERTA, VERMELHO_DANO
from src.utils.math_utils import normalizar_vetor, distancia, vetor_direcao


class Projetil:
    """
    Representa um projétil disparado pelo jogador ou inimigos.
    Suporta múltiplos tipos de sprites, dano balístico direto e detonação de área (AoE).
    """
    _sprites: dict = {}

    def __init__(
        self,
        x: float,
        y: float,
        dir_x: float = 1.0,
        dir_y: float = 0.0,
        velocidade: float = 420.0,
        dano: int = 12,
        tempo_vida: float = 2.5,
        dono: str = "jogador",
        largura: int = 8,
        altura: int = 8,
        sprite_key: str = "projetil_pistola",
        explosivo: bool = False,
        raio_explosao: float = 0.0,
        perfurante: bool = False,
        desaceleracao: float = 0.0,
        vx: float = None,
        vy: float = None,
        cor=None,
        refletido_parry: bool = False,
        splash_mult: float = 0.75,
        ja_dividido_tear: bool = False,
        **kwargs
    ):
        self.x = float(x)
        self.y = float(y)
        self.x_origem = float(x)
        self.y_origem = float(y)
        if vx is not None and vy is not None:
            self.velocidade = math.hypot(vx, vy)
            self.dir_x, self.dir_y = normalizar_vetor(vx, vy)
        else:
            self.dir_x, self.dir_y = normalizar_vetor(dir_x, dir_y)
            self.velocidade = float(velocidade)
        self.desaceleracao = float(desaceleracao)
        self.dano = int(dano)
        self.tempo_vida = float(tempo_vida)
        self.tempo_vida_restante = float(tempo_vida)
        self.dono = dono
        self.largura = int(largura)
        self.altura = int(altura)
        self.width = self.largura
        self.height = self.altura
        self.sprite_key = sprite_key
        self.cor = cor
        self.explosivo = bool(explosivo)
        self.raio_explosao = float(raio_explosao)
        self.perfurante = bool(perfurante)
        self.alvos_atingidos = set()
        self.ativo = True
        self.requer_detonacao_ao_expirar = False
        self._cached_rot_surf = None
        self._cached_rot_key = None

        self.parried: bool = bool(kwargs.get("parried", refletido_parry))
        self.refletido_parry: bool = bool(refletido_parry or self.parried)
        self.splash_mult: float = float(splash_mult)
        self.ja_dividido_tear: bool = bool(ja_dividido_tear)
        self.superaquecido: bool = bool(kwargs.get("superaquecido", False))
        self.sobrecarregado: bool = bool(kwargs.get("sobrecarregado", False))
        self.perfuracoes_restantes: int = int(kwargs.get("perfuracoes_restantes", 0))
        self.knockback_forca: float = float(kwargs.get("knockback_forca", 0.0))
        self.aceleracao: float = float(kwargs.get("aceleracao", 0.0))
        self.chao_em_chamas: bool = bool(kwargs.get("chao_em_chamas", False))
        self.arco_parabolico: bool = bool(kwargs.get("arco_parabolico", False))
        self.fragmentar: bool = bool(kwargs.get("fragmentar", False))
        self.critico_nativo: bool = bool(kwargs.get("critico_nativo", False))
        self.chance_critico_arma: float = float(kwargs.get("chance_critico_arma", 0.0))
        self.trilha_plasma: bool = bool(kwargs.get("trilha_plasma", False))
        self.origem_trilha: tuple = kwargs.get("origem_trilha", (self.x_origem, self.y_origem))
        self.recuo_autor: float = float(kwargs.get("recuo_autor", 0.0))

    @property
    def vx(self) -> float:
        return self.dir_x * self.velocidade

    @property
    def vy(self) -> float:
        return self.dir_y * self.velocidade

    @classmethod
    def _carregar_sprite(cls, sprite_key: str):
        if sprite_key not in cls._sprites:
            try:
                caminho = obter_caminho_asset(sprite_key)
                if os.path.isfile(caminho):
                    cls._sprites[sprite_key] = pygame.image.load(caminho).convert_alpha()
                else:
                    cls._sprites[sprite_key] = None
            except Exception:
                cls._sprites[sprite_key] = None
        return cls._sprites.get(sprite_key)

    def update(self, dt: float):
        """Atualiza a posição do projétil, desacelera se aplicável e decrementa o tempo de vida."""
        if not self.ativo:
            return

        if getattr(self, "aceleracao", 0.0) > 0.0:
            self.velocidade = min(850.0, self.velocidade + self.aceleracao * dt)

        if self.desaceleracao > 0.0:
            self.velocidade = max(0.0, self.velocidade - self.desaceleracao * dt)

        self.x += self.dir_x * self.velocidade * dt
        self.y += self.dir_y * self.velocidade * dt
        self.tempo_vida_restante -= dt

        if self.tempo_vida_restante <= 0.0:
            self.ativo = False
            if self.explosivo:
                self.requer_detonacao_ao_expirar = True

    def explodir(
        self,
        lista_inimigos: list,
        jogador=None,
        config_sistema=None,
        mult_dano_explosivo: float = 1.0,
        alvo_direto=None
    ) -> list:
        """
        Executa a detonação em área (AoE) do projétil explosivo.
        O alvo de impacto direto recebe 2x de dano (Direct Hit Bonus).
        Demais inimigos no raio de explosão recebem 1x de dano.
        Se Fogo Amigo estiver ativo, aplica dano ao jogador e/ou aos drones do jogador.
        """
        if not self.explosivo or self.raio_explosao <= 0.0:
            return []

        self.requer_detonacao_ao_expirar = False
        self.ativo = False

        centro_x = self.x + self.largura / 2.0
        centro_y = self.y + self.altura / 2.0
        dano_efetivo = int(round(self.dano * mult_dano_explosivo))

        inimigos_afetados = []
        for inimigo in lista_inimigos:
            if not getattr(inimigo, "vivo", True) or getattr(inimigo, "em_fase", False):
                continue

            e_cx = inimigo.x + getattr(inimigo, "largura", 28) / 2.0
            e_cy = inimigo.y + getattr(inimigo, "altura", 28) / 2.0
            dist = distancia(centro_x, centro_y, e_cx, e_cy)

            dir_ataque = vetor_direcao(centro_x, centro_y, e_cx, e_cy)
            if dir_ataque == (0.0, 0.0):
                dir_ataque = (self.dir_x, self.dir_y)

            if inimigo is alvo_direto:
                # Bônus de impacto direto: 2x de dano
                try:
                    inimigo.receber_dano(
                        dano_efetivo * 2,
                        origem_x=centro_x,
                        origem_y=centro_y,
                        dir_ataque=dir_ataque
                    )
                except TypeError:
                    inimigo.receber_dano(dano_efetivo * 2)
                inimigos_afetados.append(inimigo)
                if hasattr(inimigo, "aplicar_knockback"):
                    inimigo.aplicar_knockback(self.dir_x, self.dir_y, forca=350.0)
            elif dist <= self.raio_explosao:
                try:
                    inimigo.receber_dano(
                        dano_efetivo,
                        origem_x=centro_x,
                        origem_y=centro_y,
                        dir_ataque=dir_ataque
                    )
                except TypeError:
                    inimigo.receber_dano(dano_efetivo)
                inimigos_afetados.append(inimigo)

                # Aplica knockback radial a partir do epicentro da explosão
                if dist > 0.1 and hasattr(inimigo, "aplicar_knockback"):
                    kx = (e_cx - centro_x) / dist
                    ky = (e_cy - centro_y) / dist
                    inimigo.aplicar_knockback(kx, ky, forca=280.0)

        # Checa fogo amigo para o jogador e drones
        auto_dano_ativo = False
        if config_sistema is not None and getattr(self, "dono", "jogador") == "jogador":
            if hasattr(config_sistema, "obter_modificadores"):
                mods = config_sistema.obter_modificadores()
                auto_dano_ativo = getattr(mods, "auto_dano", False)
            elif hasattr(config_sistema, "obter_valor"):
                auto_dano_ativo = (config_sistema.obter_valor("fogo_amigo") == "ligado")

        if auto_dano_ativo and jogador is not None and getattr(jogador, "vivo", True):
            j_cx = jogador.x + getattr(jogador, "largura", 32) / 2.0
            j_cy = jogador.y + getattr(jogador, "altura", 32) / 2.0
            dist_j = distancia(centro_x, centro_y, j_cx, j_cy)
            if dist_j <= self.raio_explosao:
                try:
                    jogador.receber_dano(dano_efetivo, causa_morte="Fogo Amigo (Explosão própria)")
                except TypeError:
                    jogador.receber_dano(dano_efetivo)

            # Destruição de todos os drones companheiros por fogo amigo (1 HP)
            drones_list = []
            if hasattr(jogador, "drones") and jogador.drones:
                drones_list = list(jogador.drones)
            elif getattr(jogador, "drone", None) is not None:
                drones_list = [jogador.drone]

            for dr in drones_list:
                if getattr(dr, "ativo", True):
                    d_cx = dr.x + getattr(dr, "largura", 24) / 2.0
                    d_cy = dr.y + getattr(dr, "altura", 24) / 2.0
                    dist_d = distancia(centro_x, centro_y, d_cx, d_cy)
                    if dist_d <= self.raio_explosao:
                        dr.receber_dano(dano_efetivo)

        # Reproduz efeito sonoro de explosão
        try:
            from PPlay.sound import Sound
            sfx = Sound(obter_caminho_asset("sfx_explosao"))
            sfx.play()
        except Exception:
            pass

        return inimigos_afetados

    def get_rect(self) -> tuple[float, float, int, int]:
        """Retorna (x, y, largura, altura) para teste de colisão AABB."""
        return (self.x, self.y, self.largura, self.altura)

    def clonar(
        self,
        vx: float = None,
        vy: float = None,
        x: float = None,
        y: float = None,
        cor: tuple = None
    ) -> "Projetil":
        """
        Cria e retorna uma cópia independente do projétil atual.
        Preserva atributos críticos balísticos e explosivos (raio_explosao, sprite_key,
        desaceleracao, perfurante, explosivo, largura, altura, dano, tempo_vida,
        tempo_vida_restante, x_origem, y_origem, alvos_atingidos e dono),
        permitindo override opcional de velocidade vetorial (vx, vy), posição (x, y) e cor.
        """
        pos_x = self.x if x is None else float(x)
        pos_y = self.y if y is None else float(y)
        cor_clone = self.cor if cor is None else cor

        if vx is not None and vy is not None:
            clone = Projetil(
                x=pos_x,
                y=pos_y,
                vx=vx,
                vy=vy,
                dano=self.dano,
                tempo_vida=self.tempo_vida,
                dono=self.dono,
                largura=self.largura,
                altura=self.altura,
                sprite_key=self.sprite_key,
                explosivo=self.explosivo,
                raio_explosao=self.raio_explosao,
                perfurante=self.perfurante,
                desaceleracao=self.desaceleracao,
                cor=cor_clone
            )
        else:
            clone = Projetil(
                x=pos_x,
                y=pos_y,
                dir_x=self.dir_x,
                dir_y=self.dir_y,
                velocidade=self.velocidade,
                dano=self.dano,
                tempo_vida=self.tempo_vida,
                dono=self.dono,
                largura=self.largura,
                altura=self.altura,
                sprite_key=self.sprite_key,
                explosivo=self.explosivo,
                raio_explosao=self.raio_explosao,
                perfurante=self.perfurante,
                desaceleracao=self.desaceleracao,
                cor=cor_clone
            )

        clone.tempo_vida_restante = self.tempo_vida_restante
        clone.x_origem = self.x_origem
        clone.y_origem = self.y_origem
        clone.alvos_atingidos = set(self.alvos_atingidos)
        clone.parried = getattr(self, "parried", False)
        clone.refletido_parry = getattr(self, "refletido_parry", False)
        clone.splash_mult = float(getattr(self, "splash_mult", 0.75))
        clone.ja_dividido_tear = bool(getattr(self, "ja_dividido_tear", False))
        clone.superaquecido = getattr(self, "superaquecido", False)
        clone.sobrecarregado = getattr(self, "sobrecarregado", False)
        clone.perfuracoes_restantes = getattr(self, "perfuracoes_restantes", 0)
        clone.knockback_forca = getattr(self, "knockback_forca", 0.0)
        clone.aceleracao = getattr(self, "aceleracao", 0.0)
        clone.chao_em_chamas = getattr(self, "chao_em_chamas", False)
        clone.arco_parabolico = getattr(self, "arco_parabolico", False)
        clone.fragmentar = getattr(self, "fragmentar", False)
        clone.critico_nativo = getattr(self, "critico_nativo", False)
        clone.chance_critico_arma = getattr(self, "chance_critico_arma", 0.0)
        clone.trilha_plasma = getattr(self, "trilha_plasma", False)
        clone.origem_trilha = getattr(self, "origem_trilha", (self.x_origem, self.y_origem))
        clone.recuo_autor = getattr(self, "recuo_autor", 0.0)
        return clone

    def desenhar(self, janela, camera=None):
        """Renderiza o projétil na tela virtual com coordenadas de câmera e rotação direcional."""
        if not self.ativo:
            return

        draw_x = camera.transform_x(self.x) if camera else self.x
        draw_y = camera.transform_y(self.y) if camera else self.y

        largura_janela = getattr(janela, "largura", 800)
        altura_janela = getattr(janela, "altura", 600)
        screen = getattr(janela, "screen", janela)
        is_low_graphics = getattr(janela, "low_graphics", False)

        # Não desenha se estiver completamente fora da tela visível
        if draw_x < -30 or draw_x > largura_janela + 30 or draw_y < -30 or draw_y > altura_janela + 30:
            return

        if getattr(self, "arco_parabolico", False):
            prog = 1.0 - (self.tempo_vida_restante / max(0.01, self.tempo_vida))
            altura_z = math.sin(max(0.0, min(1.0, prog)) * math.pi) * 28.0
            sombra_rect = pygame.Rect(int(draw_x), int(draw_y + self.altura), self.largura, max(4, self.altura // 2))
            pygame.draw.ellipse(screen, (10, 12, 18), sombra_rect)
            draw_y -= altura_z

        # Fallback/cor configurada ou derivada do sprite
        cor = self.cor
        if cor is None:
            cor = AMARELO_XP
            if "foguete" in self.sprite_key or "granada" in self.sprite_key:
                cor = LARANJA_ALERTA
            elif "inimigo" in self.sprite_key:
                cor = VERMELHO_DANO

        # Trilhas de alto contraste para projéteis refletidos por parry e tiros sobrecarregados
        cx_proj = draw_x + self.largura / 2.0
        cy_proj = draw_y + self.altura / 2.0
        is_refletido = getattr(self, "refletido_parry", False) or getattr(self, "parried", False)
        is_sobrecarregado = getattr(self, "sobrecarregado", False)

        if is_refletido:
            tail_len = 28.0 if not is_low_graphics else 18.0
            tx = cx_proj - self.dir_x * tail_len
            ty = cy_proj - self.dir_y * tail_len
            pygame.draw.line(screen, (255, 195, 40), (int(cx_proj), int(cy_proj)), (int(tx), int(ty)), 5 if not is_low_graphics else 3)
            if not is_low_graphics:
                tx_core = cx_proj - self.dir_x * (tail_len * 0.7)
                ty_core = cy_proj - self.dir_y * (tail_len * 0.7)
                pygame.draw.line(screen, (255, 250, 185), (int(cx_proj), int(cy_proj)), (int(tx_core), int(ty_core)), 2)
        elif is_sobrecarregado:
            tail_len = 26.0 if not is_low_graphics else 16.0
            tx = cx_proj - self.dir_x * tail_len
            ty = cy_proj - self.dir_y * tail_len
            pygame.draw.line(screen, (0, 230, 255), (int(cx_proj), int(cy_proj)), (int(tx), int(ty)), 5 if not is_low_graphics else 3)
            if not is_low_graphics:
                tx_core = cx_proj - self.dir_x * (tail_len * 0.72)
                ty_core = cy_proj - self.dir_y * (tail_len * 0.72)
                pygame.draw.line(screen, (255, 225, 90), (int(cx_proj), int(cy_proj)), (int(tx_core), int(ty_core)), 2)

        # Modo low_graphics: desenha diretamente primitivas geométricas sem texturas/rotação pesada
        if is_low_graphics:
            pygame.draw.rect(
                screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura)
            )
            if is_refletido or is_sobrecarregado or getattr(self, "critico_nativo", False):
                raio_dourado = max(self.largura, self.altura) // 2 + 3
                centro_dourado = (int(cx_proj), int(cy_proj))
                cor_anel = (255, 225, 90) if is_refletido else ((0, 230, 255) if is_sobrecarregado else (255, 215, 0))
                pygame.draw.circle(screen, cor_anel, centro_dourado, raio_dourado, width=1)
            return

        sprite = self._carregar_sprite(self.sprite_key)
        if sprite is not None:
            # Garante escala do sprite compatível com a largura e altura do projétil
            if sprite.get_width() != self.largura or sprite.get_height() != self.altura:
                escala_key = (self.sprite_key, self.largura, self.altura)
                if getattr(self, "_cached_scaled_key", None) != escala_key or getattr(self, "_cached_scaled_surf", None) is None:
                    self._cached_scaled_key = escala_key
                    self._cached_scaled_surf = pygame.transform.scale(sprite, (self.largura, self.altura))
                sprite = self._cached_scaled_surf

            # Rotaciona foguetes, granadas e projéteis balísticos de acordo com o vetor de disparo
            if "foguete" in self.sprite_key or "granada" in self.sprite_key or "rifle" in self.sprite_key or "pistola" in self.sprite_key or "minigun" in self.sprite_key:
                ang_deg = -math.degrees(math.atan2(self.dir_y, self.dir_x))
                rot_key = (self.sprite_key, self.largura, self.altura, round(ang_deg, 1))
                if getattr(self, "_cached_rot_key", None) != rot_key or getattr(self, "_cached_rot_surf", None) is None:
                    self._cached_rot_key = rot_key
                    self._cached_rot_surf = pygame.transform.rotate(sprite, ang_deg)
                rot_sprite = self._cached_rot_surf
                rot_rect = rot_sprite.get_rect(center=(int(cx_proj), int(cy_proj)))
                screen.blit(rot_sprite, rot_rect)
            else:
                screen.blit(sprite, (int(draw_x), int(draw_y)))
        else:
            pygame.draw.rect(
                screen,
                cor,
                (int(draw_x), int(draw_y), self.largura, self.altura)
            )

        if is_refletido:
            raio_dourado = max(self.largura, self.altura) // 2 + 4
            pygame.draw.circle(screen, (255, 225, 90), (int(cx_proj), int(cy_proj)), raio_dourado, width=2)
        elif is_sobrecarregado:
            raio_dourado = max(self.largura, self.altura) // 2 + 3
            pygame.draw.circle(screen, (0, 230, 255), (int(cx_proj), int(cy_proj)), raio_dourado, width=2)
            pygame.draw.circle(screen, (255, 225, 90), (int(cx_proj), int(cy_proj)), max(2, raio_dourado - 2), width=1)
        elif getattr(self, "critico_nativo", False):
            raio_dourado = max(self.largura, self.altura) // 2 + 3
            pygame.draw.circle(screen, (255, 215, 0), (int(cx_proj), int(cy_proj)), raio_dourado, width=1)
