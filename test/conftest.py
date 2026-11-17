# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

conftest
configuração comum da suíte de testes do cls.common

2026.nov  mlabru  fixture catalog_migrado (autouse): o banco dos testes nasce
                  migrado (cls_common.dbase.schema), como em produção
2026.nov  mlabru  initial version (Linux/Python)
"""
# < imports >──────────────────────────────────────────────────────────────────────────

# python library
import os

# pytest
import pytest

# < ambiente cls >─────────────────────────────────────────────────────────────────────

# a suíte não depende do cls.env de quem a roda (~/.config/cls/cls.env)
os.environ["CLS_ENV_FILE"] = os.devnull

# < catalog.db migrado >───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def catalog_migrado(tmp_path):
    """
    todo teste começa com <tmp_path>/catalog.db já na versão de esquema do
    código, como um banco de produção depois do deploy (o deploy migra; os
    programas só conferem).  Para um banco NÃO migrado, use outro nome
    """
    # locals (import tardio: o sys.path é montado acima)
    import cls_common.dbase.schema as sc

    sc.migrate(str(tmp_path / "catalog.db"))

# < the end >──────────────────────────────────────────────────────────────────────────
