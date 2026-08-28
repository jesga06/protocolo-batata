"""
Gerador Procedural de Assets — Protocolo: Batata
Gera todos os sprites PNG (jogador, inimigos, armas, projéteis, equipamentos, drops, tiles, UI)
e arquivos de áudio WAV (SFX 8-bit e música de fase) utilizando Pillow, wave, struct e math.
"""

import os
import math
import struct
import wave
import random
from PIL import Image, ImageDraw

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")


# =============================================================================
# 1. FUNÇÕES AUXILIARES DE DESENHO PIXEL ART COM PILLOW
# =============================================================================

def criar_imagem_transparente(largura: int, altura: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    return img, draw


def salvar_png(img: Image.Image, caminho_relativo: str):
    caminho_completo = os.path.join(ASSETS_DIR, caminho_relativo)
    os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
    img.save(caminho_completo, "PNG")
    print(f"  [PNG] Gerado: {caminho_relativo} ({img.width}x{img.height})")


# =============================================================================
# 2. SPRITES DO JOGADOR (BATATA COMBATENTE)
# =============================================================================

def desenhar_batata(draw: ImageDraw.ImageDraw, ox: int, oy: int, dano: bool = False, frame_walk: int = 0):
    """
    Desenha o avatar da Batata Mecânica (32x32) com pés, antena, olhos cibernéticos e detalhes.
    """
    # Cores
    if dano:
        cor_corpo = (255, 100, 100, 255)
        cor_sombra = (180, 40, 40, 255)
        cor_contorno = (120, 20, 20, 255)
        cor_olho = (255, 255, 255, 255)
        cor_brilho = (255, 220, 220, 255)
    else:
        cor_corpo = (205, 155, 75, 255)       # Dourado Batata
        cor_sombra = (145, 95, 45, 255)      # Sombra inferior
        cor_contorno = (80, 50, 25, 255)     # Contorno
        cor_olho = (0, 230, 255, 255)        # Olhos cibernéticos ciano
        cor_brilho = (235, 195, 120, 255)   # Destaque superior

    # Pés / Esteiras mecânicas (com animação de caminhada)
    cor_pes = (60, 65, 75, 255)
    if frame_walk == 0:
        draw.rectangle([ox + 8, oy + 26, ox + 13, oy + 30], fill=cor_pes, outline=cor_contorno)
        draw.rectangle([ox + 18, oy + 26, ox + 23, oy + 30], fill=cor_pes, outline=cor_contorno)
    elif frame_walk == 1:
        draw.rectangle([ox + 7, oy + 25, ox + 12, oy + 29], fill=cor_pes, outline=cor_contorno)
        draw.rectangle([ox + 19, oy + 27, ox + 24, oy + 31], fill=cor_pes, outline=cor_contorno)
    elif frame_walk == 2:
        draw.rectangle([ox + 8, oy + 26, ox + 13, oy + 30], fill=cor_pes, outline=cor_contorno)
        draw.rectangle([ox + 18, oy + 26, ox + 23, oy + 30], fill=cor_pes, outline=cor_contorno)
    elif frame_walk == 3:
        draw.rectangle([ox + 9, oy + 27, ox + 14, oy + 31], fill=cor_pes, outline=cor_contorno)
        draw.rectangle([ox + 17, oy + 25, ox + 22, oy + 29], fill=cor_pes, outline=cor_contorno)

    # Corpo oval da batata (18x22)
    # Sombra inferior
    draw.ellipse([ox + 6, oy + 6, ox + 25, oy + 27], fill=cor_sombra, outline=cor_contorno)
    # Corpo principal
    draw.ellipse([ox + 7, oy + 6, ox + 24, oy + 25], fill=cor_corpo)
    # Destaque superior esquerdo
    draw.ellipse([ox + 9, oy + 8, ox + 17, oy + 15], fill=cor_brilho)

    # Manchas naturais de batata / rebites mecânicos
    cor_mancha = (165, 115, 55, 255) if not dano else (200, 60, 60, 255)
    draw.point([ox + 10, oy + 19], fill=cor_mancha)
    draw.point([ox + 11, oy + 19], fill=cor_mancha)
    draw.point([ox + 20, oy + 18], fill=cor_mancha)
    draw.point([ox + 18, oy + 11], fill=cor_mancha)

    # Antena no topo da cabeça
    draw.line([ox + 15, oy + 6, ox + 15, oy + 2], fill=(100, 110, 120, 255), width=1)
    draw.ellipse([ox + 14, oy + 1, ox + 16, oy + 3], fill=(255, 50, 50, 255)) # Luz vermelha

    # Olhos cibernéticos / Visor
    draw.rectangle([ox + 10, oy + 13, ox + 13, oy + 16], fill=cor_olho, outline=cor_contorno)
    draw.rectangle([ox + 18, oy + 13, ox + 21, oy + 16], fill=cor_olho, outline=cor_contorno)
    # Pupilas / Reflexo
    draw.point([ox + 11, oy + 14], fill=(255, 255, 255, 255))
    draw.point([ox + 19, oy + 14], fill=(255, 255, 255, 255))

    # Cinto de utilidades / Faixa metálica
    draw.line([ox + 8, oy + 21, ox + 23, oy + 21], fill=(50, 55, 65, 255), width=1)
    draw.rectangle([ox + 14, oy + 20, ox + 17, oy + 22], fill=(220, 180, 40, 255)) # Fivela dourada


def gerar_sprites_jogador():
    # 1. Idle (32x32)
    img_idle, draw_idle = criar_imagem_transparente(32, 32)
    desenhar_batata(draw_idle, 0, 0, dano=False, frame_walk=0)
    salvar_png(img_idle, "sprites/jogador/batata_idle.png")

    # 2. Walk Spritesheet (128x32 - 4 frames de 32x32)
    img_walk, draw_walk = criar_imagem_transparente(128, 32)
    for frame in range(4):
        desenhar_batata(draw_walk, frame * 32, 0, dano=False, frame_walk=frame)
    salvar_png(img_walk, "sprites/jogador/batata_walk_sheet.png")

    # 3. Dano (32x32)
    img_dano, draw_dano = criar_imagem_transparente(32, 32)
    desenhar_batata(draw_dano, 0, 0, dano=True, frame_walk=0)
    salvar_png(img_dano, "sprites/jogador/batata_dano.png")


# =============================================================================
# 3. SPRITES DOS INIMIGOS
# =============================================================================

def gerar_sprites_inimigos():
    # 1. Inimigo Padrão / Estagiário (32x32) - Robô azul com visor vermelho e garras
    img, draw = criar_imagem_transparente(32, 32)
    # Corpo
    draw.rectangle([7, 8, 24, 25], fill=(60, 120, 210, 255), outline=(20, 40, 90, 255))
    # Cabeça / Cúpula
    draw.ellipse([8, 3, 23, 12], fill=(80, 150, 240, 255), outline=(20, 40, 90, 255))
    # Visor vermelho ameaçador
    draw.rectangle([10, 7, 21, 10], fill=(255, 30, 60, 255))
    draw.point([12, 8], fill=(255, 200, 200, 255))
    # Garras laterais
    draw.line([4, 14, 7, 16], fill=(180, 190, 205, 255), width=2)
    draw.line([24, 16, 27, 14], fill=(180, 190, 205, 255), width=2)
    # Pernas mecânicas
    draw.line([10, 25, 8, 30], fill=(40, 45, 60, 255), width=2)
    draw.line([21, 25, 23, 30], fill=(40, 45, 60, 255), width=2)
    salvar_png(img, "sprites/inimigos/inimigo_padrao.png")

    # 2. Inimigo Tanque / Geladeira Industrial (48x48) - Pesado, blindado
    img, draw = criar_imagem_transparente(48, 48)
    # Corpo volumoso
    draw.rectangle([8, 8, 39, 41], fill=(100, 115, 130, 255), outline=(30, 35, 45, 255))
    # Portas / Placas de aço
    draw.line([8, 24, 39, 24], fill=(40, 45, 55, 255), width=2)
    # Grades de ventilação
    for y in [30, 34, 38]:
        draw.line([14, y, 33, y], fill=(40, 45, 55, 255), width=1)
    # Visores amarelos furiosos
    draw.rectangle([14, 13, 20, 17], fill=(255, 200, 0, 255), outline=(50, 40, 0, 255))
    draw.rectangle([27, 13, 33, 17], fill=(255, 200, 0, 255), outline=(50, 40, 0, 255))
    # Rebites de aço nos cantos
    for rx, ry in [(10, 10), (37, 10), (10, 39), (37, 39)]:
        draw.point([rx, ry], fill=(220, 230, 240, 255))
    # Esteiras pesadas
    draw.rectangle([4, 12, 8, 38], fill=(50, 55, 65, 255), outline=(20, 25, 30, 255))
    draw.rectangle([39, 12, 43, 38], fill=(50, 55, 65, 255), outline=(20, 25, 30, 255))
    salvar_png(img, "sprites/inimigos/inimigo_tank.png")

    # 3. Inimigo Rápido / Viciado em Cafeína (24x24) - Pequeno, neon verde/amarelo
    img, draw = criar_imagem_transparente(24, 24)
    # Corpo aerodinâmico em cunha
    draw.polygon([(12, 2), (21, 19), (3, 19)], fill=(180, 255, 0, 255), outline=(50, 90, 0, 255))
    # Núcleo de energia neon
    draw.polygon([(12, 6), (17, 16), (7, 16)], fill=(255, 255, 100, 255))
    # Olho vermelho único
    draw.ellipse([10, 9, 14, 13], fill=(255, 0, 60, 255))
    # Raios / Faíscas
    draw.line([12, 19, 10, 23], fill=(0, 255, 220, 255), width=1)
    draw.line([12, 19, 14, 23], fill=(0, 255, 220, 255), width=1)
    salvar_png(img, "sprites/inimigos/inimigo_rapido.png")

    # 4. Inimigo Phasing / Fantasma Tecnológico (32x32) - Semi-transparente ciano
    img, draw = criar_imagem_transparente(32, 32)
    cor_phasing = (0, 240, 255, 160)
    cor_phasing_brilho = (180, 255, 255, 220)
    draw.ellipse([6, 5, 25, 24], fill=cor_phasing, outline=(0, 150, 200, 180))
    draw.polygon([(6, 20), (10, 29), (14, 20), (18, 29), (22, 20), (25, 27)], fill=cor_phasing)
    # Olhos brilhantes
    draw.ellipse([10, 11, 14, 15], fill=cor_phasing_brilho)
    draw.ellipse([18, 11, 22, 15], fill=cor_phasing_brilho)
    salvar_png(img, "sprites/inimigos/inimigo_phasing.png")

    # 5. Inimigo Blindado / Ballistic Enthusiast (36x36) - Casca de titânio
    img, draw = criar_imagem_transparente(36, 36)
    # Escudo frontal resistente
    draw.rounded_rectangle([4, 4, 31, 31], radius=6, fill=(120, 130, 145, 255), outline=(40, 45, 55, 255), width=2)
    # Placa reforçada em X
    draw.line([8, 8, 27, 27], fill=(70, 75, 85, 255), width=2)
    draw.line([27, 8, 8, 27], fill=(70, 75, 85, 255), width=2)
    # Fenda de visão estreita
    draw.rectangle([10, 16, 25, 19], fill=(255, 80, 0, 255), outline=(0, 0, 0, 255))
    salvar_png(img, "sprites/inimigos/inimigo_blindado.png")

    # 6. Inimigo Ranged / Atirador Blaster (32x32) - Laranja/ferrugem com canhão
    img, draw = criar_imagem_transparente(32, 32)
    # Corpo
    draw.rectangle([8, 9, 23, 24], fill=(230, 110, 25, 255), outline=(80, 30, 0, 255))
    # Canhão / Lançador frontal
    draw.rectangle([22, 14, 29, 18], fill=(60, 65, 75, 255), outline=(20, 20, 20, 255))
    draw.ellipse([27, 14, 30, 18], fill=(255, 0, 100, 255)) # Focinho de energia
    # Lente de mira telescópica
    draw.ellipse([11, 11, 17, 17], fill=(0, 255, 200, 255), outline=(0, 80, 60, 255))
    # Pernas tripé
    draw.line([9, 24, 5, 30], fill=(50, 55, 60, 255), width=2)
    draw.line([16, 24, 16, 30], fill=(50, 55, 60, 255), width=2)
    draw.line([22, 24, 26, 30], fill=(50, 55, 60, 255), width=2)
    salvar_png(img, "sprites/inimigos/inimigo_ranged.png")


# =============================================================================
# 4. SPRITES DE ARMAS
# =============================================================================

def gerar_sprites_armas():
    # 1. Arma Melee / Chave Inglesa (24x24)
    img, draw = criar_imagem_transparente(24, 24)
    # Cabo diagonal
    draw.line([5, 19, 15, 9], fill=(160, 170, 180, 255), width=3)
    draw.line([4, 20, 8, 16], fill=(50, 55, 65, 255), width=3) # Empunhadura
    # Cabeça da chave inglesa
    draw.polygon([(14, 10), (19, 5), (22, 8), (17, 13)], fill=(190, 200, 215, 255), outline=(80, 90, 100, 255))
    draw.polygon([(17, 7), (20, 4), (22, 6), (19, 9)], fill=(0, 0, 0, 0)) # Vão da chave
    salvar_png(img, "sprites/armas/arma_melee.png")

    # 2. Arma Pistola (24x24)
    img, draw = criar_imagem_transparente(24, 24)
    # Slide / Cano
    draw.rectangle([6, 7, 20, 12], fill=(140, 150, 165, 255), outline=(40, 45, 55, 255))
    # Empunhadura
    draw.polygon([(8, 12), (13, 12), (11, 20), (6, 20)], fill=(70, 50, 35, 255), outline=(30, 20, 10, 255))
    # Gatilho
    draw.line([13, 14, 13, 16], fill=(200, 200, 200, 255), width=1)
    salvar_png(img, "sprites/armas/arma_pistola.png")

    # 3. Arma Minigun (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    # Tambor de munição
    draw.ellipse([4, 14, 14, 24], fill=(50, 55, 65, 255), outline=(20, 20, 25, 255))
    # Corpo
    draw.rectangle([10, 11, 20, 20], fill=(80, 85, 95, 255), outline=(30, 30, 35, 255))
    # Canos rotativos múltiplos
    for y in [12, 15, 18]:
        draw.line([20, y, 30, y], fill=(170, 180, 190, 255), width=2)
    draw.line([29, 11, 29, 20], fill=(40, 45, 50, 255), width=1)
    salvar_png(img, "sprites/armas/arma_minigun.png")

    # 4. Arma Shotgun (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    # Coronha de madeira
    draw.polygon([(2, 18), (10, 14), (10, 19), (2, 22)], fill=(120, 70, 35, 255), outline=(50, 30, 15, 255))
    # Armação de metal
    draw.rectangle([10, 13, 18, 18], fill=(90, 95, 105, 255), outline=(30, 35, 40, 255))
    # Cano duplo longo
    draw.rectangle([18, 12, 30, 16], fill=(160, 170, 180, 255), outline=(40, 45, 50, 255))
    # Guarda-mão / Bomba
    draw.rectangle([17, 16, 23, 19], fill=(120, 70, 35, 255), outline=(50, 30, 15, 255))
    salvar_png(img, "sprites/armas/arma_shotgun.png")

    # 5. Arma Rifle de Assalto (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    # Coronha
    draw.rectangle([3, 14, 9, 18], fill=(60, 65, 70, 255), outline=(20, 25, 30, 255))
    # Corpo receptor
    draw.rectangle([9, 12, 21, 17], fill=(85, 95, 105, 255), outline=(30, 35, 40, 255))
    # Carregador curvado
    draw.polygon([(13, 17), (17, 17), (15, 25), (12, 24)], fill=(45, 50, 55, 255), outline=(20, 20, 20, 255))
    # Cano e mira
    draw.rectangle([21, 13, 30, 16], fill=(140, 150, 160, 255), outline=(30, 35, 40, 255))
    draw.rectangle([13, 9, 18, 12], fill=(40, 45, 50, 255)) # Mira óptica
    salvar_png(img, "sprites/armas/arma_rifle.png")

    # 6. Arma Lança-Foguetes (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    # Tubo de lançamento verde-oliva
    draw.rectangle([4, 11, 28, 20], fill=(75, 95, 55, 255), outline=(30, 45, 20, 255))
    # Bocal de exaustão traseiro
    draw.polygon([(4, 10), (1, 8), (1, 23), (4, 21)], fill=(50, 55, 60, 255), outline=(20, 20, 20, 255))
    # Boca frontal
    draw.ellipse([25, 11, 29, 20], fill=(40, 50, 30, 255), outline=(20, 30, 15, 255))
    # Empunhadura dupla
    draw.rectangle([10, 20, 13, 26], fill=(40, 40, 45, 255))
    draw.rectangle([18, 20, 21, 26], fill=(40, 40, 45, 255))
    salvar_png(img, "sprites/armas/arma_foguetes.png")

    # 7. Arma Lança-Granadas (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    # Coronha
    draw.line([3, 20, 10, 15], fill=(50, 55, 60, 255), width=3)
    # Tambor de granadas giratório
    draw.ellipse([10, 10, 20, 21], fill=(110, 120, 130, 255), outline=(40, 45, 50, 255))
    # Cano grosso
    draw.rectangle([20, 11, 29, 18], fill=(70, 75, 80, 255), outline=(25, 30, 35, 255))
    draw.ellipse([27, 11, 30, 18], fill=(30, 30, 35, 255))
    salvar_png(img, "sprites/armas/arma_granadas.png")


# =============================================================================
# 5. SPRITES DE PROJÉTEIS
# =============================================================================

def gerar_sprites_projeteis():
    # 1. Projétil Pistola (8x8)
    img, draw = criar_imagem_transparente(8, 8)
    draw.ellipse([1, 2, 6, 5], fill=(255, 220, 0, 255), outline=(200, 120, 0, 255))
    draw.point([3, 3], fill=(255, 255, 255, 255))
    salvar_png(img, "sprites/projeteis/projetil_pistola.png")

    # 2. Projétil Minigun (6x6)
    img, draw = criar_imagem_transparente(6, 6)
    draw.rectangle([1, 2, 4, 3], fill=(255, 160, 20, 255))
    draw.point([3, 2], fill=(255, 255, 200, 255))
    salvar_png(img, "sprites/projeteis/projetil_minigun.png")

    # 3. Projétil Shotgun (8x8)
    img, draw = criar_imagem_transparente(8, 8)
    draw.ellipse([2, 2, 5, 5], fill=(220, 60, 20, 255), outline=(255, 180, 60, 255))
    salvar_png(img, "sprites/projeteis/projetil_shotgun.png")

    # 4. Projétil Rifle (10x10)
    img, draw = criar_imagem_transparente(10, 10)
    draw.polygon([(1, 4), (8, 2), (9, 5), (8, 8), (1, 6)], fill=(0, 230, 255, 255), outline=(0, 100, 180, 255))
    draw.line([3, 5, 7, 5], fill=(255, 255, 255, 255))
    salvar_png(img, "sprites/projeteis/projetil_rifle.png")

    # 5. Projétil Foguete (20x10)
    img, draw = criar_imagem_transparente(20, 10)
    # Rastro de fogo
    draw.polygon([(0, 5), (5, 2), (5, 8)], fill=(255, 80, 0, 255))
    draw.polygon([(2, 5), (5, 3), (5, 7)], fill=(255, 220, 0, 255))
    # Corpo do míssil
    draw.rectangle([5, 2, 14, 7], fill=(80, 100, 60, 255), outline=(30, 40, 20, 255))
    # Ogiva
    draw.polygon([(14, 2), (19, 5), (14, 7)], fill=(220, 30, 30, 255), outline=(100, 10, 10, 255))
    # Aletas
    draw.polygon([(5, 1), (8, 2), (5, 2)], fill=(40, 45, 50, 255))
    draw.polygon([(5, 8), (8, 7), (5, 7)], fill=(40, 45, 50, 255))
    salvar_png(img, "sprites/projeteis/projetil_foguete.png")

    # 6. Projétil Granada (12x12)
    img, draw = criar_imagem_transparente(12, 12)
    draw.ellipse([2, 3, 9, 10], fill=(60, 85, 45, 255), outline=(25, 40, 15, 255))
    draw.rectangle([5, 1, 7, 3], fill=(160, 170, 180, 255)) # Pino
    draw.point([6, 1], fill=(255, 0, 0, 255)) # LED piscante
    salvar_png(img, "sprites/projeteis/projetil_granada.png")

    # 7. Projétil Inimigo (10x10) - Esfera de plasma roxa
    img, draw = criar_imagem_transparente(10, 10)
    draw.ellipse([1, 1, 8, 8], fill=(210, 40, 240, 255), outline=(100, 10, 140, 255))
    draw.ellipse([3, 3, 6, 6], fill=(255, 180, 255, 255))
    salvar_png(img, "sprites/projeteis/projetil_inimigo.png")


# =============================================================================
# 6. SPRITES DE EQUIPAMENTOS (DRONES)
# =============================================================================

def gerar_sprites_equipamentos():
    # 1. Drone de Cura (24x24) - Branco e verde com cruz médica
    img, draw = criar_imagem_transparente(24, 24)
    # Hélices
    draw.ellipse([2, 3, 8, 6], fill=(180, 230, 200, 200))
    draw.ellipse([16, 3, 22, 6], fill=(180, 230, 200, 200))
    # Corpo arredondado
    draw.ellipse([5, 6, 19, 19], fill=(245, 250, 245, 255), outline=(40, 140, 70, 255), width=2)
    # Cruz verde
    draw.rectangle([10, 9, 14, 16], fill=(35, 190, 75, 255))
    draw.rectangle([8, 11, 16, 14], fill=(35, 190, 75, 255))
    salvar_png(img, "sprites/equipamentos/drone_cura.png")

    # 2. Drone de Combate (24x24) - Cinza chumbo angular com canhões duplos
    img, draw = criar_imagem_transparente(24, 24)
    # Hélices
    draw.ellipse([1, 4, 7, 7], fill=(150, 160, 175, 200))
    draw.ellipse([17, 4, 23, 7], fill=(150, 160, 175, 200))
    # Chassi militar
    draw.polygon([(12, 4), (20, 12), (16, 19), (8, 19), (4, 12)], fill=(75, 80, 90, 255), outline=(30, 35, 40, 255))
    # Canhões frontais
    draw.line([7, 19, 7, 23], fill=(220, 30, 30, 255), width=2)
    draw.line([17, 19, 17, 23], fill=(220, 30, 30, 255), width=2)
    # Olho vermelho central
    draw.ellipse([10, 10, 14, 14], fill=(255, 0, 50, 255))
    salvar_png(img, "sprites/equipamentos/drone_combate.png")

    # 3. Drone de Suporte (24x24) - Azul diamante gerador de escudo
    img, draw = criar_imagem_transparente(24, 24)
    # Anel de energia
    draw.ellipse([3, 3, 21, 21], outline=(0, 220, 255, 200), width=1)
    # Núcleo diamante
    draw.polygon([(12, 4), (19, 12), (12, 20), (5, 12)], fill=(40, 90, 180, 255), outline=(0, 200, 255, 255))
    draw.polygon([(12, 7), (16, 12), (12, 17), (8, 12)], fill=(180, 240, 255, 255))
    salvar_png(img, "sprites/equipamentos/drone_suporte.png")


# =============================================================================
# 7. SPRITES DE DROPS (CAIXAS COLETÁVEIS)
# =============================================================================

def desenhar_caixa_base(draw: ImageDraw.ImageDraw, cor_primaria: tuple, cor_secundaria: tuple, cor_borda: tuple):
    # Caixa de madeira/aço 24x24
    draw.rectangle([2, 2, 21, 21], fill=cor_primaria, outline=cor_borda, width=1)
    # Reforços nos cantos
    for rx, ry in [(2, 2), (19, 2), (2, 19), (19, 19)]:
        draw.rectangle([rx, ry, rx + 2, ry + 2], fill=cor_secundaria)
    # Travessa transversal
    draw.line([3, 11, 20, 11], fill=cor_borda, width=1)


def gerar_sprites_drops():
    # 1. Drop XP (24x24) - Roxo com gema amarela
    img, draw = criar_imagem_transparente(24, 24)
    desenhar_caixa_base(draw, (110, 40, 160, 255), (70, 20, 110, 255), (45, 10, 75, 255))
    # Gema dourada de XP no centro
    draw.polygon([(12, 5), (17, 11), (12, 17), (7, 11)], fill=(255, 215, 0, 255), outline=(180, 130, 0, 255))
    draw.point([12, 11], fill=(255, 255, 220, 255))
    salvar_png(img, "sprites/drops/drop_xp.png")

    # 2. Drop Cura (24x24) - Vermelho com cruz branca
    img, draw = criar_imagem_transparente(24, 24)
    desenhar_caixa_base(draw, (200, 45, 45, 255), (140, 25, 25, 255), (80, 10, 10, 255))
    # Cruz branca médica
    draw.rectangle([10, 6, 13, 16], fill=(255, 255, 255, 255))
    draw.rectangle([7, 9, 16, 13], fill=(255, 255, 255, 255))
    salvar_png(img, "sprites/drops/drop_cura.png")

    # 3. Drop Arma (24x24) - Marrom militar com pistola
    img, draw = criar_imagem_transparente(24, 24)
    desenhar_caixa_base(draw, (115, 75, 45, 255), (75, 45, 25, 255), (45, 25, 15, 255))
    # Ícone dourado de arma
    draw.rectangle([7, 8, 16, 11], fill=(255, 200, 50, 255))
    draw.rectangle([8, 11, 11, 15], fill=(255, 200, 50, 255))
    salvar_png(img, "sprites/drops/drop_arma.png")

    # 4. Drop Equipamento (24x24) - Laranja com engrenagem
    img, draw = criar_imagem_transparente(24, 24)
    desenhar_caixa_base(draw, (220, 100, 20, 255), (150, 60, 10, 255), (85, 30, 5, 255))
    # Ícone de chave / ferramenta
    draw.ellipse([8, 7, 15, 14], fill=(255, 255, 255, 255), outline=(50, 50, 50, 255))
    draw.ellipse([10, 9, 13, 12], fill=(220, 100, 20, 255))
    salvar_png(img, "sprites/drops/drop_equipamento.png")

    # 5. Drop Configuração (24x24) - Platina com engrenagem dourada
    img, draw = criar_imagem_transparente(24, 24)
    desenhar_caixa_base(draw, (90, 105, 120, 255), (55, 65, 75, 255), (30, 35, 40, 255))
    # Engrenagem dourada brilhante
    draw.ellipse([7, 6, 16, 15], fill=(255, 220, 40, 255), outline=(160, 120, 10, 255))
    draw.ellipse([9, 8, 14, 13], fill=(90, 105, 120, 255))
    for ang in [0, 45, 90, 135]:
        rad = math.radians(ang)
        dx = int(5 * math.cos(rad))
        dy = int(5 * math.sin(rad))
        draw.point([11 + dx, 10 + dy], fill=(255, 240, 100, 255))
    salvar_png(img, "sprites/drops/drop_config.png")


# =============================================================================
# 8. TILES E CENÁRIO
# =============================================================================

def gerar_tiles():
    # 1. Piso Tecnológico Padrão (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    draw.rectangle([0, 0, 31, 31], fill=(28, 32, 40, 255))
    draw.rectangle([1, 1, 30, 30], outline=(40, 46, 58, 255))
    # Linhas de grade sutis
    draw.line([0, 15, 31, 15], fill=(22, 25, 32, 255), width=1)
    draw.line([15, 0, 15, 31], fill=(22, 25, 32, 255), width=1)
    # Rebites de canto
    for rx, ry in [(3, 3), (28, 3), (3, 28), (28, 28)]:
        draw.point([rx, ry], fill=(60, 70, 85, 255))
    salvar_png(img, "tiles/tile_piso.png")

    # 2. Piso Tecnológico Alternativo / Circuito (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    draw.rectangle([0, 0, 31, 31], fill=(30, 35, 44, 255))
    draw.rectangle([1, 1, 30, 30], outline=(45, 52, 65, 255))
    # Circuito ciano sutil
    draw.line([8, 15, 23, 15], fill=(0, 180, 210, 160), width=1)
    draw.line([15, 8, 15, 23], fill=(0, 180, 210, 160), width=1)
    draw.ellipse([13, 13, 17, 17], fill=(0, 220, 255, 220))
    salvar_png(img, "tiles/tile_piso_alt.png")

    # 3. Parede de Limite da Arena (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    draw.rectangle([0, 0, 31, 31], fill=(45, 50, 60, 255), outline=(15, 18, 22, 255), width=2)
    # Efeito 3D chanfrado
    draw.rectangle([3, 3, 28, 12], fill=(70, 78, 92, 255))
    draw.rectangle([3, 13, 28, 28], fill=(35, 40, 48, 255))
    draw.line([0, 0, 31, 0], fill=(110, 120, 140, 255), width=1) # Brilho topo
    salvar_png(img, "tiles/tile_parede.png")

    # 4. Obstáculo / Caixa Industrial (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    draw.rectangle([2, 2, 29, 29], fill=(110, 75, 45, 255), outline=(45, 30, 15, 255), width=2)
    # Reforços em X
    draw.line([3, 3, 28, 28], fill=(75, 50, 30, 255), width=2)
    draw.line([28, 3, 3, 28], fill=(75, 50, 30, 255), width=2)
    # Parafusos
    for rx, ry in [(4, 4), (27, 4), (4, 27), (27, 27)]:
        draw.point([rx, ry], fill=(180, 190, 200, 255))
    salvar_png(img, "tiles/obstaculo_caixa.png")


# =============================================================================
# 9. ASSETS DE INTERFACE DE USUÁRIO (UI)
# =============================================================================

def gerar_assets_ui():
    # 1. Botão Engrenagem HUD (32x32)
    img, draw = criar_imagem_transparente(32, 32)
    draw.ellipse([4, 4, 27, 27], fill=(40, 45, 55, 230), outline=(0, 220, 255, 255), width=2)
    # Engrenagem
    draw.ellipse([9, 9, 22, 22], fill=(200, 215, 230, 255), outline=(80, 95, 110, 255))
    draw.ellipse([13, 13, 18, 18], fill=(40, 45, 55, 255))
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        dx = int(7 * math.cos(rad))
        dy = int(7 * math.sin(rad))
        draw.rectangle([14 + dx, 14 + dy, 16 + dx, 16 + dy], fill=(200, 215, 230, 255))
    salvar_png(img, "ui/btn_gear.png")

    # 2. Card de Upgrade Level Up (160x220)
    img, draw = criar_imagem_transparente(160, 220)
    # Fundo escuro glassmorphic
    draw.rounded_rectangle([2, 2, 157, 217], radius=8, fill=(20, 24, 32, 245), outline=(0, 200, 255, 255), width=2)
    # Borda interna dourada sutil
    draw.rounded_rectangle([6, 6, 153, 213], radius=6, outline=(255, 215, 0, 160), width=1)
    # Cabeçalho do card
    draw.rectangle([7, 7, 152, 45], fill=(30, 40, 60, 255))
    draw.line([7, 45, 152, 45], fill=(0, 220, 255, 255), width=2)
    # Moldura central para o ícone
    draw.rectangle([54, 55, 105, 106], fill=(12, 15, 22, 255), outline=(0, 220, 255, 200), width=1)
    salvar_png(img, "ui/card_upgrade_bg.png")

    # 3. Slot de Inventário (40x40)
    img, draw = criar_imagem_transparente(40, 40)
    draw.rectangle([1, 1, 38, 38], fill=(18, 22, 30, 240), outline=(60, 75, 95, 255), width=2)
    # Cantoneiras ciano
    for cx, cy in [(3, 3), (34, 3), (3, 34), (34, 34)]:
        draw.point([cx, cy], fill=(0, 220, 255, 255))
    salvar_png(img, "ui/slot_inventario.png")

    # 4. Botão Normal (180x45)
    img, draw = criar_imagem_transparente(180, 45)
    draw.rounded_rectangle([1, 1, 178, 43], radius=6, fill=(30, 38, 52, 255), outline=(0, 180, 220, 255), width=2)
    draw.line([4, 4, 175, 4], fill=(80, 110, 150, 255), width=1) # Brilho topo
    salvar_png(img, "ui/btn_bg_normal.png")

    # 5. Botão Hover (180x45)
    img, draw = criar_imagem_transparente(180, 45)
    draw.rounded_rectangle([1, 1, 178, 43], radius=6, fill=(45, 65, 95, 255), outline=(255, 215, 0, 255), width=2)
    draw.line([4, 4, 175, 4], fill=(120, 170, 230, 255), width=1)
    salvar_png(img, "ui/btn_bg_hover.png")

    # 6. Mira Crosshair (16x16)
    img, draw = criar_imagem_transparente(16, 16)
    draw.point([7, 7], fill=(255, 0, 50, 255))
    draw.point([8, 7], fill=(255, 0, 50, 255))
    draw.point([7, 8], fill=(255, 0, 50, 255))
    draw.point([8, 8], fill=(255, 0, 50, 255))
    # Linhas de mira
    draw.line([7, 1, 7, 4], fill=(0, 255, 255, 255), width=1)
    draw.line([7, 11, 7, 14], fill=(0, 255, 255, 255), width=1)
    draw.line([1, 7, 4, 7], fill=(0, 255, 255, 255), width=1)
    draw.line([11, 7, 14, 7], fill=(0, 255, 255, 255), width=1)
    salvar_png(img, "ui/mira_crosshair.png")


# =============================================================================
# 10. ÍCONES DE CONFIGURAÇÃO (20 GAMEPLAY + 3 SISTEMA = 23 ÍCONES)
# =============================================================================

def desenhar_base_icone(draw: ImageDraw.ImageDraw, cor_borda: tuple = (0, 200, 255, 255)):
    draw.rectangle([1, 1, 30, 30], fill=(15, 20, 30, 255), outline=cor_borda, width=1)


def gerar_icones_configs():
    icones = {}

    # 1. FPS Cap
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.ellipse([6, 6, 25, 25], outline=(255, 215, 0, 255), width=1)
    draw.line([15, 15, 15, 9], fill=(255, 50, 50, 255), width=2)
    draw.line([15, 15, 21, 15], fill=(255, 215, 0, 255), width=2)
    icones["icon_fps_cap.png"] = img

    # 2. Qualidade Gráfica
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([6, 6, 15, 15], fill=(255, 80, 80, 255))
    draw.rectangle([16, 16, 25, 25], fill=(80, 180, 255, 255))
    icones["icon_graficos_qualidade.png"] = img

    # 3. Resolução
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([6, 8, 25, 23], outline=(0, 255, 200, 255), width=1)
    draw.line([8, 10, 12, 10], fill=(255, 255, 255, 255), width=1)
    draw.line([19, 21, 23, 21], fill=(255, 255, 255, 255), width=1)
    icones["icon_resolucao.png"] = img

    # 4. VSync
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.line([15, 5, 15, 26], fill=(0, 220, 255, 255), width=2)
    draw.line([6, 10, 12, 10], fill=(255, 200, 0, 255), width=2)
    draw.line([18, 21, 24, 21], fill=(255, 200, 0, 255), width=2)
    icones["icon_vsync.png"] = img

    # 5. Screen Shake
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([8, 8, 23, 23], outline=(255, 100, 0, 255), width=1)
    draw.line([4, 15, 7, 15], fill=(255, 255, 0, 255), width=2)
    draw.line([24, 15, 27, 15], fill=(255, 255, 0, 255), width=2)
    icones["icon_screen_shake.png"] = img

    # 6. Motion Blur
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.ellipse([16, 10, 26, 20], fill=(0, 255, 255, 255))
    draw.ellipse([11, 10, 21, 20], fill=(0, 200, 220, 160))
    draw.ellipse([6, 10, 16, 20], fill=(0, 150, 180, 80))
    icones["icon_motion_blur.png"] = img

    # 7. HUD
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([5, 6, 26, 10], fill=(230, 40, 50, 255))
    draw.rectangle([5, 13, 20, 16], fill=(255, 215, 0, 255))
    draw.rectangle([5, 20, 12, 26], outline=(0, 220, 255, 255), width=1)
    icones["icon_hud.png"] = img

    # 8. Números de Dano
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    # "+99"
    draw.line([6, 12, 12, 12], fill=(255, 220, 0, 255), width=2)
    draw.line([9, 9, 9, 15], fill=(255, 220, 0, 255), width=2)
    draw.rectangle([15, 8, 20, 16], fill=(255, 50, 50, 255))
    draw.rectangle([22, 8, 27, 16], fill=(255, 50, 50, 255))
    icones["icon_damage_numbers.png"] = img

    # 9. Zoom
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.ellipse([6, 6, 20, 20], outline=(0, 220, 255, 255), width=2)
    draw.line([17, 17, 26, 26], fill=(200, 215, 230, 255), width=3)
    draw.line([13, 9, 13, 17], fill=(255, 215, 0, 255), width=1)
    draw.line([9, 13, 17, 13], fill=(255, 215, 0, 255), width=1)
    icones["icon_zoom.png"] = img

    # 10. Movimento pelo Mouse
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rounded_rectangle([10, 6, 21, 25], radius=5, outline=(255, 255, 255, 255), width=1)
    draw.line([15, 7, 15, 13], fill=(0, 220, 255, 255), width=2) # Roda do mouse
    icones["icon_movimento_mouse.png"] = img

    # 11. Modificadores de Teclas (Keybinds)
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([12, 6, 19, 13], fill=(50, 60, 80, 255), outline=(0, 200, 255, 255)) # W
    draw.rectangle([5, 15, 12, 22], fill=(50, 60, 80, 255), outline=(0, 200, 255, 255))  # A
    draw.rectangle([13, 15, 20, 22], fill=(50, 60, 80, 255), outline=(0, 200, 255, 255)) # S
    draw.rectangle([21, 15, 28, 22], fill=(50, 60, 80, 255), outline=(0, 200, 255, 255)) # D
    icones["icon_keybinds.png"] = img

    # 12. Suavização de Câmera
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([6, 9, 21, 23], fill=(60, 70, 85, 255), outline=(180, 200, 220, 255))
    draw.polygon([(21, 12), (27, 8), (27, 24), (21, 20)], fill=(0, 200, 255, 255))
    icones["icon_suavizacao_camera.png"] = img

    # 13. Disparo Automático
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.ellipse([6, 12, 12, 18], fill=(255, 200, 0, 255))
    draw.ellipse([14, 12, 20, 18], fill=(255, 150, 0, 255))
    draw.ellipse([22, 12, 28, 18], fill=(255, 50, 0, 255))
    icones["icon_auto_fire.png"] = img

    # 14. Inimigos à Distância
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.polygon([(10, 6), (22, 15), (10, 24)], fill=(255, 100, 0, 255), outline=(255, 200, 0, 255))
    draw.ellipse([23, 13, 27, 17], fill=(255, 0, 80, 255))
    icones["icon_inimigos_ranged.png"] = img

    # 15. Captura de Drops por Inimigos (Coleta Inimiga)
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([6, 10, 16, 20], fill=(160, 60, 220, 255), outline=(255, 215, 0, 255)) # Caixa
    draw.line([16, 15, 26, 8], fill=(255, 50, 80, 255), width=2) # Garra puxando
    draw.line([26, 8, 23, 5], fill=(255, 50, 80, 255), width=2)
    icones["icon_coleta_inimiga.png"] = img

    # 16. Velocidade dos Inimigos
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.polygon([(4, 18), (14, 6), (18, 14), (28, 8), (20, 26)], fill=(0, 255, 150, 255), outline=(0, 100, 50, 255))
    icones["icon_velocidade_inimigos.png"] = img

    # 17. Vida dos Inimigos
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.polygon([(16, 5), (26, 10), (22, 24), (16, 28), (10, 24), (6, 10)], fill=(220, 40, 40, 255), outline=(255, 200, 200, 255))
    draw.rectangle([14, 11, 18, 21], fill=(255, 255, 255, 255))
    draw.rectangle([10, 14, 22, 18], fill=(255, 255, 255, 255))
    icones["icon_vida_inimigos.png"] = img

    # 18. Iluminação Dinâmica
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.polygon([(6, 12), (12, 8), (12, 24), (6, 20)], fill=(80, 90, 105, 255)) # Lanterna
    draw.polygon([(12, 13), (27, 5), (27, 27), (12, 19)], fill=(255, 255, 150, 180)) # Facho de luz
    icones["icon_iluminacao.png"] = img

    # 19. Cores Invertidas
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.rectangle([6, 6, 15, 25], fill=(255, 255, 255, 255))
    draw.rectangle([16, 6, 25, 25], fill=(20, 20, 20, 255), outline=(255, 255, 255, 255))
    icones["icon_cores_invertidas.png"] = img

    # 20. Fogo Amigo
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw, cor_borda=(255, 50, 50, 255))
    # Caveira de alerta
    draw.ellipse([8, 6, 23, 19], fill=(255, 60, 60, 255))
    draw.rectangle([11, 18, 20, 24], fill=(255, 60, 60, 255))
    draw.ellipse([10, 10, 14, 14], fill=(0, 0, 0, 255))
    draw.ellipse([17, 10, 21, 14], fill=(0, 0, 0, 255))
    icones["icon_fogo_amigo.png"] = img

    # Sistema: Volume Master
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.polygon([(6, 12), (12, 12), (18, 6), (18, 26), (12, 20), (6, 20)], fill=(0, 220, 255, 255))
    draw.arc([16, 8, 26, 24], -60, 60, fill=(255, 215, 0, 255), width=2)
    icones["icon_volume_master.png"] = img

    # Sistema: Volume Música
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.ellipse([7, 19, 13, 25], fill=(255, 100, 200, 255))
    draw.ellipse([17, 16, 23, 22], fill=(255, 100, 200, 255))
    draw.line([13, 21, 13, 8], fill=(255, 100, 200, 255), width=2)
    draw.line([23, 18, 23, 6], fill=(255, 100, 200, 255), width=2)
    draw.line([13, 8, 23, 6], fill=(255, 100, 200, 255), width=3)
    icones["icon_volume_musica.png"] = img

    # Sistema: Volume SFX
    img, draw = criar_imagem_transparente(32, 32)
    desenhar_base_icone(draw)
    draw.polygon([(6, 12), (11, 12), (16, 7), (16, 25), (11, 20), (6, 20)], fill=(255, 200, 50, 255))
    draw.line([19, 11, 24, 8], fill=(255, 80, 0, 255), width=2)
    draw.line([20, 16, 26, 16], fill=(255, 80, 0, 255), width=2)
    draw.line([19, 21, 24, 24], fill=(255, 80, 0, 255), width=2)
    icones["icon_volume_sfx.png"] = img

    for nome, img in icones.items():
        salvar_png(img, f"ui/icones_configs/{nome}")


# =============================================================================
# 11. GERADOR PROCEDURAL DE ÁUDIO 8-BIT (WAV PCM 16-BIT 44.1kHz)
# =============================================================================

SAMPLE_RATE = 44100


def salvar_wav(dados_pcm: list[float], caminho_relativo: str, canais: int = 1):
    caminho_completo = os.path.join(ASSETS_DIR, caminho_relativo)
    os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
    with wave.open(caminho_completo, "w") as wav_file:
        wav_file.setnchannels(canais)
        wav_file.setsampwidth(2) # 16 bits = 2 bytes
        wav_file.setframerate(SAMPLE_RATE)

        # Converter floats [-1.0, 1.0] em inteiros 16-bit signed [-32767, 32767]
        frames = bytearray()
        for amostra in dados_pcm:
            amostra_clamped = max(-1.0, min(1.0, amostra))
            amostra_int = int(amostra_clamped * 32767)
            frames.extend(struct.pack("<h", amostra_int))
        wav_file.writeframes(frames)
    print(f"  [WAV] Gerado: {caminho_relativo} ({len(dados_pcm) / SAMPLE_RATE:.2f}s)")


def sintetizar_som_tiro(freq_inicial: float, freq_final: float, duracao: float, ruido: float = 0.0) -> list[float]:
    num_amostras = int(SAMPLE_RATE * duracao)
    amostras = []
    fase = 0.0
    for i in range(num_amostras):
        t = i / num_amostras
        freq = freq_inicial + (freq_final - freq_inicial) * (t ** 0.6)
        fase += 2.0 * math.pi * freq / SAMPLE_RATE

        # Onda quadrada com duty cycle variável
        onda = 1.0 if (fase % (2.0 * math.pi)) < math.pi else -1.0
        if ruido > 0:
            onda = (1.0 - ruido) * onda + ruido * random.uniform(-1.0, 1.0)

        # Envelope de decaimento exponencial
        envelope = math.exp(-4.5 * t)
        amostras.append(onda * envelope * 0.7)
    return amostras


def sintetizar_explosao(duracao: float = 0.5) -> list[float]:
    num_amostras = int(SAMPLE_RATE * duracao)
    amostras = []
    ultimo_val = 0.0
    for i in range(num_amostras):
        t = i / num_amostras
        # Ruído branco filtrado passa-baixa
        r = random.uniform(-1.0, 1.0)
        ultimo_val = 0.85 * ultimo_val + 0.15 * r
        # Modulação com onda senoidal grave
        seno_grave = math.sin(2.0 * math.pi * 55.0 * (i / SAMPLE_RATE))
        envelope = math.exp(-3.5 * t)
        amostras.append((ultimo_val * 0.7 + seno_grave * 0.3) * envelope * 0.85)
    return amostras


def sintetizar_arpeggio(notas_freq: list[float], duracao_nota: float, tipo_onda: str = "square") -> list[float]:
    amostras = []
    for freq in notas_freq:
        num_amostras = int(SAMPLE_RATE * duracao_nota)
        fase = 0.0
        for i in range(num_amostras):
            t = i / num_amostras
            fase += 2.0 * math.pi * freq / SAMPLE_RATE
            if tipo_onda == "square":
                onda = 1.0 if (fase % (2.0 * math.pi)) < math.pi else -1.0
            elif tipo_onda == "triangle":
                onda = (2.0 / math.pi) * math.asin(math.sin(fase))
            else:
                onda = math.sin(fase)

            envelope = math.exp(-3.0 * t)
            amostras.append(onda * envelope * 0.6)
    return amostras


def gerar_efeitos_sonoros():
    # Tiros
    salvar_wav(sintetizar_som_tiro(850, 180, 0.12, 0.05), "audio/sfx/tiro_pistola.wav")
    salvar_wav(sintetizar_som_tiro(600, 120, 0.07, 0.10), "audio/sfx/tiro_minigun.wav")
    salvar_wav(sintetizar_som_tiro(400, 90, 0.22, 0.40), "audio/sfx/tiro_shotgun.wav")
    salvar_wav(sintetizar_som_tiro(1100, 250, 0.10, 0.02), "audio/sfx/tiro_rifle.wav")
    salvar_wav(sintetizar_som_tiro(200, 500, 0.35, 0.30), "audio/sfx/tiro_foguete.wav")
    salvar_wav(sintetizar_som_tiro(350, 100, 0.18, 0.20), "audio/sfx/tiro_granada.wav")

    # Ataque Melee (Whoosh)
    salvar_wav(sintetizar_som_tiro(300, 700, 0.15, 0.15), "audio/sfx/ataque_melee.wav")

    # Explosão
    salvar_wav(sintetizar_explosao(0.55), "audio/sfx/explosao.wav")

    # Dano e Morte
    salvar_wav(sintetizar_som_tiro(220, 80, 0.18, 0.25), "audio/sfx/dano_jogador.wav")
    salvar_wav(sintetizar_arpeggio([350, 280, 210, 140, 70], 0.14, "square"), "audio/sfx/morte_jogador.wav")
    salvar_wav(sintetizar_som_tiro(450, 150, 0.12, 0.10), "audio/sfx/morte_inimigo.wav")

    # Coleta de Itens (Pickups)
    salvar_wav(sintetizar_arpeggio([523.25, 659.25, 783.99], 0.06, "triangle"), "audio/sfx/pickup_xp.wav")
    salvar_wav(sintetizar_arpeggio([440.00, 554.37, 659.25], 0.08, "triangle"), "audio/sfx/pickup_cura.wav")
    salvar_wav(sintetizar_arpeggio([300.00, 450.00], 0.08, "square"), "audio/sfx/pickup_arma.wav")
    salvar_wav(sintetizar_arpeggio([392.00, 587.33, 880.00], 0.07, "square"), "audio/sfx/pickup_equipamento.wav")

    # Level Up Fanfare
    salvar_wav(sintetizar_arpeggio([523.25, 659.25, 783.99, 1046.50], 0.14, "square"), "audio/sfx/levelup.wav")

    # UI Buttons
    salvar_wav(sintetizar_som_tiro(900, 900, 0.04, 0.0), "audio/sfx/btn_hover.wav")
    salvar_wav(sintetizar_som_tiro(600, 950, 0.08, 0.0), "audio/sfx/btn_click.wav")


def gerar_musica_fase():
    """
    Gera uma trilha sonora 8-bit chiptune procedural em loop contínuo (~6.4 segundos).
    Possui linha de baixo (triangle), melodia arpejada (pulse/square) e ritmo de bateria 8-bit.
    """
    bpm = 135
    segundos_por_tempo = 60.0 / bpm
    duracao_colcheia = segundos_por_tempo / 2.0  # 16 colcheias = 8 tempos = 2 compassos
    total_compassos = 4
    total_colcheias = total_compassos * 8
    duracao_total = total_colcheias * duracao_colcheia

    num_amostras = int(SAMPLE_RATE * duracao_total)
    dados = [0.0] * num_amostras

    # Progressão harmônica: Am - F - C - G
    acordes_baixo = [
        110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0, 110.0,  # A2
        87.31, 87.31, 87.31, 87.31, 87.31, 87.31, 87.31, 87.31,    # F2
        130.81, 130.81, 130.81, 130.81, 130.81, 130.81, 130.81, 130.81,  # C3
        98.00, 98.00, 98.00, 98.00, 98.00, 98.00, 98.00, 98.00     # G2
    ]

    melodia = [
        440.0, 523.25, 659.25, 523.25, 440.0, 659.25, 587.33, 523.25,  # Am
        349.23, 440.0, 523.25, 440.0, 349.23, 523.25, 440.0, 392.0,    # F
        523.25, 659.25, 783.99, 659.25, 523.25, 783.99, 659.25, 587.33, # C
        392.0, 493.88, 587.33, 493.88, 392.0, 587.33, 659.25, 587.33   # G
    ]

    fase_baixo = 0.0
    fase_melodia = 0.0
    amostras_por_colcheia = int(SAMPLE_RATE * duracao_colcheia)

    for i in range(num_amostras):
        idx_colcheia = min(len(acordes_baixo) - 1, i // amostras_por_colcheia)
        t_colcheia = (i % amostras_por_colcheia) / amostras_por_colcheia

        # 1. Linha de Baixo (Onda Triangular pulsante)
        freq_b = acordes_baixo[idx_colcheia]
        fase_baixo += 2.0 * math.pi * freq_b / SAMPLE_RATE
        onda_baixo = (2.0 / math.pi) * math.asin(math.sin(fase_baixo))
        env_baixo = math.exp(-1.8 * t_colcheia)

        # 2. Melodia Lead (Onda Quadrada 8-bit)
        freq_m = melodia[idx_colcheia]
        fase_melodia += 2.0 * math.pi * freq_m / SAMPLE_RATE
        onda_melodia = 1.0 if (fase_melodia % (2.0 * math.pi)) < (math.pi * 0.7) else -1.0
        env_melodia = math.exp(-2.2 * t_colcheia)

        # 3. Ritmo / Bateria 8-bit (Hi-hat e Caixa com ruído nos tempos pares)
        ruido_ritmo = 0.0
        if idx_colcheia % 2 == 1:
            # Caixa (snare)
            ruido_ritmo = random.uniform(-1.0, 1.0) * math.exp(-10.0 * t_colcheia) * 0.3
        elif t_colcheia < 0.2:
            # Hi-hat fechado
            ruido_ritmo = random.uniform(-1.0, 1.0) * math.exp(-25.0 * t_colcheia) * 0.15

        # Mixagem master
        amostra_mix = (onda_baixo * env_baixo * 0.35) + (onda_melodia * env_melodia * 0.30) + ruido_ritmo
        dados[i] = amostra_mix * 0.85

    salvar_wav(dados, "audio/musica/musica_fase.wav")


# =============================================================================
# 12. EXECUÇÃO PRINCIPAL
# =============================================================================

def gerar_todos_os_assets():
    print("==================================================")
    print("INICIANDO GERAÇÃO PROCEDURAL DE ASSETS — PROTOCOLO: BATATA")
    print(f"Diretório de destino: {ASSETS_DIR}")
    print("==================================================")

    print("\n[1/6] Gerando Sprites do Jogador...")
    gerar_sprites_jogador()

    print("\n[2/6] Gerando Sprites dos Inimigos...")
    gerar_sprites_inimigos()

    print("\n[3/6] Gerando Sprites de Armas e Projéteis...")
    gerar_sprites_armas()
    gerar_sprites_projeteis()

    print("\n[4/6] Gerando Sprites de Equipamentos e Drops...")
    gerar_sprites_equipamentos()
    gerar_sprites_drops()

    print("\n[5/6] Gerando Tiles do Cenário e Interface (UI)...")
    gerar_tiles()
    gerar_assets_ui()
    gerar_icones_configs()

    print("\n[6/6] Sintetizando Efeitos Sonoros e Trilha Sonora...")
    gerar_efeitos_sonoros()
    gerar_musica_fase()

    print("\n==================================================")
    print("SUCESSO: Todos os assets procedurais foram gerados!")
    print("==================================================")


if __name__ == "__main__":
    gerar_todos_os_assets()
