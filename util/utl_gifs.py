# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

utl_gifs

2025.nov  mlabru  initial version (Linux/Python)
"""
# < imports >--------------------------------------------------------------------------

# python library
import glob
import logging
import os
import time

# PIL
from PIL import Image, ImageEnhance

# < constants >------------------------------------------------------------------------

# gif size
GIF_SIZE = (800, 600)

# < logging >--------------------------------------------------------------------------

M_LOG = logging.getLogger(__name__)
M_LOG.setLevel(logging.INFO)

# -------------------------------------------------------------------------------------
def arquivos_estaveis(fs_folder: str, fs_ftype: str, fi_age_min: int) -> list:
    """
    retorna lista de arquivos estáveis (tempo > age_min)
    """
    # logger
    M_LOG.debug(">> arquivos_estaveis")

    # lista de arquivos
    llst_files = []
    # agora
    ltt_now = time.time()

    # for all files in folder...
    for lsf in sorted(glob.glob(f"{fs_folder}/*.{fs_ftype}")):
        # file age
        if ltt_now - os.path.getmtime(lsf) > fi_age_min:
            # salva na lista
            llst_files.append(lsf)

    # ok
    return llst_files

# -------------------------------------------------------------------------------------
def cria_gif(flst_frames: list, fs_out_dir: str):
    """
    cria GIF
    """
    # logger
    M_LOG.debug(">> cria_gif")

    # lista de imagens
    llst_imgs = []

    # for all frames...
    for lsf in flst_frames:
        # mantém a proporção e adiciona fundo preto
        l_img = redimensionar_com_proporcao(lsf, GIF_SIZE)

        # save on images list 
        llst_imgs.append(l_img)

    # cria o GIF
    llst_imgs[0].save(fs_out_dir,
                      save_all=True,
                      append_images=llst_imgs[1:],
                      duration=200,
                      loop=0)

# -------------------------------------------------------------------------------------
def make_enhancer(fimg, fs_out_path: str):
    """
    enhance image
    """
    # logger
    M_LOG.debug(">> make_enhancer")

    # frames list
    llst_frames = []

    # for n frames...
    for li in range(6):
        # enhance image
        lenhancer = ImageEnhance.Brightness(fimg)
        # blinking effect
        lf_factor = 1 + (0.2 if li % 2 == 0 else -0.2)
        # enhance image
        lframe = lenhancer.enhance(lf_factor)
        # save on images list
        llst_frames.append(lframe)

    # save GIF
    llst_frames[0].save(fs_out_path, save_all=True,
                        append_images=llst_frames[1:], duration=300, loop=0)

# -------------------------------------------------------------------------------------
def precisa_regerar(flst_files: list, f_gif_out) -> bool:
    """
    precisa regerar o GIF se tem um arquivo novo na lista
    """
    # logger
    M_LOG.debug(">> precisa_regerar")

    # GIF não existe ?
    if not os.path.exists(f_gif_out):
        # ok
        return True

    # tempo da última modificação
    ltt_mtime = os.path.getmtime(f_gif_out)

    # tempo da última imagem
    ltt_ultimo_file = max(os.path.getmtime(lsf) for lsf in flst_files)

    # ok
    return ltt_ultimo_file > ltt_mtime

# -------------------------------------------------------------------------------------
def redimensionar_com_proporcao(fs_img_path: str, ft_size: tuple[int, int]):
    """
    redimensiona a imagem mantendo as proporções
    """
    # logger
    M_LOG.debug(">> redimensionar_com_proporcao")

    # open image
    l_img = Image.open(fs_img_path)

    # calcula a escala para caber no quadro sem cortar nada
    l_img.thumbnail(ft_size, Image.Resampling.LANCZOS)

    # cria um novo fundo (preto) com o tamanho exato do mosaico
    l_background = Image.new('RGB', ft_size, (0, 0, 0))
    
    # centraliza a imagem no fundo
    lt_offset = ((ft_size[0] - l_img.width)  // 2,
                 (ft_size[1] - l_img.height) // 2)

    # copia a imagem sobre o fundo
    l_background.paste(l_img, lt_offset)

    # ok    
    return l_background

# < the end >--------------------------------------------------------------------------
