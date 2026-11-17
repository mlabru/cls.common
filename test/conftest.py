# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

conftest
configuração comum da suíte de testes do cls.common

2026.nov  mlabru  initial version (Linux/Python)
"""
# < imports >──────────────────────────────────────────────────────────────────────────

# python library
import os

# < ambiente cls >─────────────────────────────────────────────────────────────────────

# a suíte não depende do cls.env de quem a roda (~/.config/cls/cls.env)
os.environ["CLS_ENV_FILE"] = os.devnull

# < the end >──────────────────────────────────────────────────────────────────────────
