# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

cls_common
pacote Python comum aos projetos cls (repo cls.common).  Visto pelos
projetos via PYTHONPATH: CLS_PYLIB, no cls.env, aponta para cls.common/python
(cls_setup_pythonpath, em cls_common.sh).

Não importa nada aqui: "import cls_common.radar.rd_mvol" não pode puxar
h5py/numpy (os scripts de cron só leem nomes de arquivo).

2026.nov  mlabru  initial version (Linux/Python)
"""

# < the end >──────────────────────────────────────────────────────────────────────────
