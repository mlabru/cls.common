# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

test_cls_common_sh
testes das funções de heartbeat do bash/cls_common.sh (cls_heartbeat,
cls_check_heartbeat), chamadas via subprocess

2026.nov  mlabru  initial version (Linux/Python)
"""
# < imports >──────────────────────────────────────────────────────────────────────────

# python library
import pathlib
import shutil
import subprocess
import time

# pytest
import pytest

# < helpers >──────────────────────────────────────────────────────────────────────────

MPTH_LIB = pathlib.Path(__file__).resolve().parent.parent / "bash" / "cls_common.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="bash indisponível")

def _bash(fs_body: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f'source "{MPTH_LIB}"; {fs_body}'],
                          capture_output=True, text=True)

# < cls_heartbeat >────────────────────────────────────────────────────────────────────

def test_heartbeat_grava_epoch_e_iso_criando_o_diretorio(tmp_path):
    lpth = tmp_path / "sub" / "x.ok"
    li_before = int(time.time())

    assert 0 == _bash(f'cls_heartbeat "{lpth}"').returncode

    ls_epoch, ls_iso = lpth.read_text().split()
    assert li_before <= int(ls_epoch) <= int(time.time())
    assert ls_iso.endswith("Z")
    # nenhum temporário sobra
    assert ["x.ok"] == [lp.name for lp in lpth.parent.iterdir()]

def test_heartbeat_nunca_falha(tmp_path):
    # diretório no lugar do arquivo: não grava, avisa, mas rc 0 (sob set -e
    # quem chamou não pode cair por causa do heartbeat)
    lpth = tmp_path / "x.ok"
    lpth.mkdir()

    lproc = _bash(f'set -e; cls_heartbeat "{lpth}"; echo depois')

    assert 0 == lproc.returncode
    assert "depois" in lproc.stdout
    assert "heartbeat não gravado" in lproc.stderr

# < cls_check_heartbeat >──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("fs_content, fi_rc, fs_text", [
    (None, 3, "sem heartbeat"),
    ("lixo\n", 3, "sem heartbeat"),
    ("AGE60 x\n", 0, "ok há 1 min"),
    ("AGE1860 2026-11-17T00:00:00Z\n", 2, "sem sucesso há 31 min (máx 30; último 2026-11-17T00:00:00Z)"),
])
def test_check_heartbeat(tmp_path, fs_content, fi_rc, fs_text):
    lpth = tmp_path / "x.ok"

    if fs_content is not None:
        if fs_content.startswith("AGE"):
            ls_age, ls_rest = fs_content[3:].split(" ", 1)
            fs_content = f"{int(time.time()) - int(ls_age)} {ls_rest}"
        lpth.write_text(fs_content)

    lproc = _bash(f'li=0; cls_check_heartbeat rot "{lpth}" 30 || li=$?; echo "rc=$li"')

    assert f"rc={fi_rc}" in lproc.stdout
    assert f"rot {fs_text}" in lproc.stdout
    assert "" == lproc.stderr

# < the end >──────────────────────────────────────────────────────────────────────────
