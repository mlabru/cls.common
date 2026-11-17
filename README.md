# cls.common

Código comum aos projetos cls (19.dash, 21.mrad, 21.mvol, 23.blitz, 23.goes,
25.oflow, 25.u-net, 27.nowcast).  Nenhum projeto o vê por symlink: tudo chega
pelo arquivo de ambiente da instalação, o `cls.env`.

| caminho | o quê | como os projetos o veem |
|---|---|---|
| `bash/cls_common.sh` | `cls_log`, `check_log_size`, `cls_check_test_env`, `cls_setup_pythonpath` | `CLS_LIB` → `source "${CLS_LIB}/cls_common.sh"` no `<pfx>_cfg.sh` |
| `python/cls_common/` | pacote Python: `dbase` (catalog.db: esquema versionado em `dbase/schema.py`, contrato da tabela `volumes`), `radar` (leitura dos `.mvol`), `util` | `CLS_PYLIB` → `cls_setup_pythonpath` (PYTHONPATH); `import cls_common.dbase.vol_dbase` |
| `etc/cls.env.example` | modelo do `cls.env` (`CLS_LIB`, `CLS_PYLIB`, `CLS_ROOT`, `CLS_DBASE_FILE`, `CLS_CAPPI_DIR`, `CLS_ENV`) | copiar para `~/.config/cls/cls.env` (ou apontar `CLS_ENV_FILE`) |

Precedência: ambiente do processo > `cls.env` > padrões de cada `<pfx>_cfg.sh`.
`CLS_LIB` e `CLS_PYLIB` são obrigatórias: sem elas os scripts param com erro.

## Esquema do catalog.db

`python/cls_common/dbase/schema.py` é o **único** lugar com DDL do
`catalog.db` compartilhado.  Versão = `PRAGMA user_version` = número de
migrações aplicadas.  Os programas só conferem a versão (`check_schema`) e
param com erro se ela for diferente da do código; quem migra é o deploy:

```bash
# backup consistente (API de backup do SQLite; o banco é WAL e os crons
# podem estar gravando -- um cp simples poderia sair inconsistente)
python3 -c 'import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d)' \
        catalog.db catalog.db.bak
PYTHONPATH=$CLS_PYLIB python3 -m cls_common.dbase.schema catalog.db --dry-run
PYTHONPATH=$CLS_PYLIB python3 -m cls_common.dbase.schema catalog.db
PYTHONPATH=$CLS_PYLIB python3 -m cls_common.dbase.schema catalog.db --check
```

A migração roda numa transação (`BEGIN IMMEDIATE`): ou chega à versão do
código, ou o banco fica como estava.  Mudança de esquema = nova função
`_mNNN_<nome>` no fim de `MT_MIGRATIONS`; nunca editar uma migração já
aplicada.  A view `cappi_pending` não é esquema (deriva dos presets ativos do
27.nowcast) e continua sendo recriada por ele.

## Testes

```bash
~/.venv/bin/python3 -m pytest -q      # pytest.ini: pythonpath = python
```

Alterar este repo afeta todos os projetos acima: rode também as suítes deles.
`pyproject.toml` existe só para um eventual `pip install`; hoje nada o usa.
