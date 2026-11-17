# cls.common

Código comum aos projetos cls (19.dash, 21.mrad, 21.mvol, 23.blitz, 23.goes,
25.oflow, 25.u-net, 27.nowcast).  Nenhum projeto o vê por symlink: tudo chega
pelo arquivo de ambiente da instalação, o `cls.env`.

| caminho | o quê | como os projetos o veem |
|---|---|---|
| `bash/cls_common.sh` | `cls_log`, `check_log_size`, `cls_check_test_env`, `cls_setup_pythonpath` | `CLS_LIB` → `source "${CLS_LIB}/cls_common.sh"` no `<pfx>_cfg.sh` |
| `python/cls_common/` | pacote Python: `dbase` (catalog.db, contrato da tabela `volumes`), `radar` (leitura dos `.mvol`), `util` | `CLS_PYLIB` → `cls_setup_pythonpath` (PYTHONPATH); `import cls_common.dbase.vol_dbase` |
| `etc/cls.env.example` | modelo do `cls.env` (`CLS_LIB`, `CLS_PYLIB`, `CLS_ROOT`, `CLS_DBASE_FILE`, `CLS_CAPPI_DIR`, `CLS_ENV`) | copiar para `~/.config/cls/cls.env` (ou apontar `CLS_ENV_FILE`) |

Precedência: ambiente do processo > `cls.env` > padrões de cada `<pfx>_cfg.sh`.
`CLS_LIB` e `CLS_PYLIB` são obrigatórias: sem elas os scripts param com erro.

## Testes

```bash
~/.venv/bin/python3 -m pytest -q      # pytest.ini: pythonpath = python
```

Alterar este repo afeta todos os projetos acima: rode também as suítes deles.
`pyproject.toml` existe só para um eventual `pip install`; hoje nada o usa.
