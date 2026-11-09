# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

png2gif

2025.nov  mlabru  initial version (Linux/Python)
"""
# < imports >--------------------------------------------------------------------------

# python library
import sys

# PIL
from PIL import Image

# locals
import utl_gifs as utl

# -------------------------------------------------------------------------------------
def main(fv_enhance: bool = False):
    """
    convert PNG to GIF
    """
    # load image, mantém a proporção e adiciona fundo preto
    limg = utl.redimensionar_com_proporcao(sys.argv[1], utl.GIF_SIZE)

    # create GIF
    ls_gif_out = sys.argv[2]

    # enhance image ?
    if fv_enhance:
        # enhance and save as GIF
        utl.make_enhancer(limg, ls_gif_out)

    else:
        # save as simple GIF (no animation)
        limg.save(ls_gif_out, format=sys.argv[3])

# -------------------------------------------------------------------------------------

main()

# < the end >--------------------------------------------------------------------------
