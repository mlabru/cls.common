# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

schema
esquema versionado do catalog.db compartilhado -- o ÚNICO lugar com DDL das
tabelas dele.  Cada projeto continua dono lógico das suas tabelas (21.mvol:
volumes, vol_raw_observations; 27.nowcast: cappi_products, sequences), mas o
texto da DDL e a ordem das mudanças moram aqui.

versão: PRAGMA user_version do banco = número de migrações aplicadas.
- migrate(): aplica as pendentes, em ordem, numa transação (BEGIN IMMEDIATE).
  Roda no deploy, pela linha de comando (abaixo), depois do backup;
- check_schema(): os programas que gravam conferem, ao abrir, que o banco
  está exatamente na versão do código (SchemaVersionError se não): ninguém
  mais cria tabela "por garantia" ao abrir a conexão.

fora do esquema: a view cappi_pending (vol_dbase.CS_VIEW_PENDING) deriva dos
presets ativos do 27.nowcast (configuração, não estrutura) e continua sendo
recriada por ele (nwc_database._refresh_pending_view).

nova mudança de esquema = nova função _mNNN_<nome> no fim de MT_MIGRATIONS;
nunca editar uma migração já aplicada em produção.

uso:
    python3 -m cls_common.dbase.schema <catalog.db>             # migra
    python3 -m cls_common.dbase.schema <catalog.db> --check     # só confere
    python3 -m cls_common.dbase.schema <catalog.db> --dry-run   # lista pendentes

2026.nov  mlabru  initial version: migração 1 (baseline) reúne a DDL que
                  estava em vol_dbase.CVolDB, vol_catalog.ensure_schema e
                  nwc_database.create_schema (27.nowcast), inclusive as
                  correções antigas (obs_time -> timestamp, sequences.preset)
"""
# < imports >──────────────────────────────────────────────────────────────────────────

# python library
import argparse
import logging
import pathlib
import sqlite3
import sys
import time

# < constants >────────────────────────────────────────────────────────────────────────

# espera por lock de escrita (o banco é compartilhado com os crons)
MF_LOCK_TIMEOUT_S = 30.0

# --- migração 1 (baseline): o esquema de 2026.nov ------------------------------------

# 21.mvol -- volumes observados (e, por contrato, os sintéticos do nowcast)
CS_CREATE_VOLUMES = """
CREATE TABLE IF NOT EXISTS volumes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    radar          TEXT    NOT NULL,
    alcance        INTEGER NOT NULL,
    timestamp      INTEGER NOT NULL,
    fullpath       TEXT    NOT NULL,
    filesize       INTEGER,
    sha1           TEXT,
    has_mvol       INTEGER DEFAULT 1,
    has_cappi      INTEGER DEFAULT 0,
    cappi_path     TEXT,
    interpolated   INTEGER DEFAULT 0,
    predicted      INTEGER DEFAULT 0,
    status         INTEGER DEFAULT 0,
    rain_fraction  REAL,
    valid_fraction REAL,
    created_at     TEXT,
    updated_at     TEXT,
    UNIQUE(radar, alcance, timestamp))"""

# 27.nowcast grava; 21.mvol (antigo volProcess) também gravava
CS_CREATE_PROCESSING_LOG = """
CREATE TABLE IF NOT EXISTS processing_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    radar      TEXT NOT NULL,
    alcance    INTEGER NOT NULL,
    timestamp  INTEGER NOT NULL,
    step       TEXT,
    status     INTEGER,
    message    TEXT,
    created_at TEXT)"""

CS_CREATE_RADAR_SITES = """
CREATE TABLE IF NOT EXISTS radar_sites (
    radar      TEXT PRIMARY KEY,
    latitude   REAL NOT NULL,
    longitude  REAL NOT NULL,
    altitude   REAL NOT NULL,
    updated_at TEXT)"""

# 21.mvol (volDBWriter) -- observações da listagem remota; fullpath relativo
# a REMOTE_DIR (vol_catalog.check_relpath)
CS_CREATE_RAW_OBSERVATIONS = """
CREATE TABLE IF NOT EXISTS vol_raw_observations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    fullpath   TEXT    NOT NULL UNIQUE,
    mtime      REAL    NOT NULL,
    timestamp  INTEGER,
    source     TEXT    NOT NULL,
    created_at TEXT
)"""

# 27.nowcast -- um CAPPI por (volume, preset)
CS_CREATE_CAPPI_PRODUCTS = """
CREATE TABLE IF NOT EXISTS cappi_products (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    radar          TEXT    NOT NULL,
    alcance        INTEGER NOT NULL,
    timestamp      INTEGER NOT NULL,
    preset         TEXT    NOT NULL,
    origin         TEXT    NOT NULL,
    status         INTEGER NOT NULL DEFAULT 1,
    attempts       INTEGER NOT NULL DEFAULT 0,
    cappi_path     TEXT,
    rain_fraction  REAL,
    valid_fraction REAL,
    created_at     TEXT,
    updated_at     TEXT,
    UNIQUE(radar, alcance, timestamp, preset))"""

# 27.nowcast -- preset no fim: é onde o ALTER TABLE o pôs nos bancos antigos
CS_CREATE_SEQUENCES = """
CREATE TABLE IF NOT EXISTS sequences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    radar      TEXT    NOT NULL,
    alcance    INTEGER NOT NULL,
    input_1    INTEGER NOT NULL,
    input_2    INTEGER NOT NULL,
    input_3    INTEGER NOT NULL,
    input_4    INTEGER NOT NULL,
    target     INTEGER NOT NULL,
    quality    INTEGER DEFAULT 0,
    created_at TEXT,
    preset     TEXT)"""

# índices (depois das correções de coluna: o de timestamp precisa dela)
MT_CREATE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_timestamp        ON volumes(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_status           ON volumes(status)",
    "CREATE INDEX IF NOT EXISTS idx_radar_timestamp  ON volumes(radar, alcance, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_sequences_target ON sequences(target)",
    "CREATE INDEX IF NOT EXISTS idx_products_status  ON cappi_products(status)",
    "CREATE INDEX IF NOT EXISTS vol_raw_observations_idx_mtime ON vol_raw_observations(mtime)",
    "CREATE INDEX IF NOT EXISTS vol_raw_observations_idx_timestamp ON vol_raw_observations(timestamp)",
)

# < logging >──────────────────────────────────────────────────────────────────────────

# logger
M_LOG = logging.getLogger(__name__)
M_LOG.setLevel(logging.INFO)

# < SchemaVersionError >───────────────────────────────────────────────────────────────

class SchemaVersionError(sqlite3.DatabaseError):
    """
    banco numa versão de esquema diferente da do código.  Subclasse de
    sqlite3.DatabaseError: os "except sqlite3.Error" dos programas a tratam
    como qualquer falha de banco (log + rc 1), sem traceback
    """

# ─────────────────────────────────────────────────────────────────────────────────────
def _columns(fconn: sqlite3.Connection, fs_table: str) -> set:
    """
    nomes das colunas de uma tabela (PRAGMA table_info: o nome é o campo 1)
    """
    return {lt_row[1] for lt_row in fconn.execute(f"PRAGMA table_info({fs_table})")}

# ─────────────────────────────────────────────────────────────────────────────────────
def _m001_baseline(fconn: sqlite3.Connection) -> None:
    """
    migração 1: o esquema de 2026.nov, idempotente -- num banco que já o
    tem (produção) não muda estrutura nenhuma; num banco vazio cria tudo.
    Inclui as correções que antes rodavam a cada abertura:
    - vol_raw_observations.obs_time (nome antigo) -> timestamp, ou timestamp
      acrescentada a uma base anterior às duas; índice antigo removido;
    - sequences sem a coluna preset (anterior a cappi_products) ganha a
      coluna.
    """
    for ls_sql in (CS_CREATE_VOLUMES, CS_CREATE_PROCESSING_LOG, CS_CREATE_RADAR_SITES,
                   CS_CREATE_RAW_OBSERVATIONS, CS_CREATE_CAPPI_PRODUCTS, CS_CREATE_SEQUENCES):
        fconn.execute(ls_sql.strip())

    # vol_raw_observations antiga ? (a afinidade REAL de obs_time renomeada
    # não atrapalha: a comparação com volumes.timestamp é numérica)
    lset_cols = _columns(fconn, "vol_raw_observations")

    if "timestamp" not in lset_cols:
        if "obs_time" in lset_cols:
            fconn.execute("ALTER TABLE vol_raw_observations RENAME COLUMN obs_time TO timestamp")

        else:
            fconn.execute("ALTER TABLE vol_raw_observations ADD COLUMN timestamp INTEGER")

    fconn.execute("DROP INDEX IF EXISTS vol_raw_observations_idx_obs_time")

    # sequences antiga ?
    if "preset" not in _columns(fconn, "sequences"):
        fconn.execute("ALTER TABLE sequences ADD COLUMN preset TEXT")

    for ls_sql in MT_CREATE_INDEXES:
        fconn.execute(ls_sql)

# migrações, em ordem: a posição (1, 2, ...) é a versão que cada uma produz
MT_MIGRATIONS = (
    _m001_baseline,
)

# versão do esquema que este código espera
CI_SCHEMA_VERSION = len(MT_MIGRATIONS)

# ─────────────────────────────────────────────────────────────────────────────────────
def schema_version(fconn: sqlite3.Connection) -> int:
    """
    versão do esquema do banco (PRAGMA user_version; 0 = nunca migrado)
    """
    return fconn.execute("PRAGMA user_version").fetchone()[0]

# ─────────────────────────────────────────────────────────────────────────────────────
def check_schema(fconn: sqlite3.Connection, fs_dbase_path: str = "catalog.db") -> None:
    """
    confere que o banco está exatamente na versão do código.  Mais antiga:
    falta rodar a migração; mais nova: este código é anterior ao esquema (não
    pode gravar nele com segurança)

    :param fconn: conexão aberta
    :param fs_dbase_path: caminho do banco, só para a mensagem

    :raises SchemaVersionError: versão diferente de CI_SCHEMA_VERSION
    """
    li_version = schema_version(fconn)

    if li_version == CI_SCHEMA_VERSION:
        # ok
        return

    if li_version < CI_SCHEMA_VERSION:
        ls_action = f"rode: python3 -m cls_common.dbase.schema {fs_dbase_path}"

    else:
        ls_action = "atualize o cls.common deste host"

    # raise an exception
    raise SchemaVersionError(f"{fs_dbase_path}: esquema na versão {li_version}, o código espera "
                             f"{CI_SCHEMA_VERSION}; {ls_action}")

# ─────────────────────────────────────────────────────────────────────────────────────
def migrate(fs_dbase_path: str, fb_dry_run: bool = False) -> tuple:
    """
    aplica as migrações pendentes, em ordem, numa única transação de escrita
    (BEGIN IMMEDIATE): ou o banco chega à versão do código, ou fica como
    estava.  Cria o arquivo (e o diretório) se não existir.

    :param fs_dbase_path: caminho do catalog.db
    :param fb_dry_run: True = só informa o que seria aplicado

    :raises SchemaVersionError: banco mais novo que o código
    :raises sqlite3.Error: falha de banco (nada é aplicado)

    :returns: (versão antes, versão depois)
    """
    # logger
    M_LOG.debug(">> migrate")

    pathlib.Path(fs_dbase_path).parent.mkdir(parents=True, exist_ok=True)

    # isolation_level=None: as transações são explícitas (o BEGIN abaixo)
    lconn = sqlite3.connect(fs_dbase_path, timeout=MF_LOCK_TIMEOUT_S, isolation_level=None)

    try:
        lconn.execute("PRAGMA journal_mode = WAL")
        lconn.execute("BEGIN IMMEDIATE")

        li_from = schema_version(lconn)

        if li_from > CI_SCHEMA_VERSION:
            # raise an exception
            raise SchemaVersionError(f"{fs_dbase_path}: esquema na versão {li_from}, mais nova "
                                     f"que a deste código ({CI_SCHEMA_VERSION})")

        if fb_dry_run:
            for li_version in range(li_from + 1, CI_SCHEMA_VERSION + 1):
                # logger
                M_LOG.info("pendente: %d %s", li_version, MT_MIGRATIONS[li_version - 1].__name__)

            lconn.execute("ROLLBACK")
            # ok
            return li_from, li_from

        for li_version in range(li_from + 1, CI_SCHEMA_VERSION + 1):
            # logger
            M_LOG.info("aplicando %d %s", li_version, MT_MIGRATIONS[li_version - 1].__name__)
            MT_MIGRATIONS[li_version - 1](lconn)

        # user_version é transacional: só vale se o COMMIT acontecer
        lconn.execute(f"PRAGMA user_version = {CI_SCHEMA_VERSION:d}")
        lconn.execute("COMMIT")

    except BaseException:
        if lconn.in_transaction:
            lconn.execute("ROLLBACK")
        raise

    finally:
        lconn.close()

    # ok
    return li_from, CI_SCHEMA_VERSION

# ─────────────────────────────────────────────────────────────────────────────────────
def arg_parse(flst_argv: list | None = None):
    """
    lê os argumentos da linha de comando

    :returns: argparse.Namespace com dbase, check e dry_run
    """
    lparser = argparse.ArgumentParser(
                 description="Migra o catalog.db para a versão de esquema deste código.")

    lparser.add_argument("dbase", type=str, help="caminho do catalog.db compartilhado.")

    lgroup = lparser.add_mutually_exclusive_group()
    lgroup.add_argument("--check", action="store_true",
                        help="só confere a versão (rc 0 se igual à do código).")
    lgroup.add_argument("--dry-run", action="store_true",
                        help="lista as migrações pendentes, sem aplicar.")

    # ok
    return lparser.parse_args(flst_argv)

# ─────────────────────────────────────────────────────────────────────────────────────
def main(flst_argv: list | None = None) -> int:
    """
    drive app

    :returns: 0 em sucesso (--check: versão igual), 1 caso contrário
    """
    largs = arg_parse(flst_argv)

    try:
        if largs.check:
            # mode=ro: conferir nunca cria nem altera o banco
            lconn = sqlite3.connect(f"file:{largs.dbase}?mode=ro", uri=True,
                                    timeout=MF_LOCK_TIMEOUT_S)

            try:
                check_schema(lconn, largs.dbase)

            finally:
                lconn.close()

            # logger
            M_LOG.info("%s: esquema na versão %d (ok)", largs.dbase, CI_SCHEMA_VERSION)
            # ok
            return 0

        li_from, li_to = migrate(largs.dbase, largs.dry_run)

    # em caso de erro,...
    except sqlite3.Error as lerr:
        # logger
        M_LOG.error("%s", lerr)
        # quit fail
        return 1

    # logger
    M_LOG.info("%s: versão %d -> %d%s", largs.dbase, li_from, li_to,
               " (dry-run)" if largs.dry_run else "")

    # ok
    return 0

# ─────────────────────────────────────────────────────────────────────────────────────
# this is the bootstrap process

if "__main__" == __name__:
    # logger (horários do log em UTC, como todo o resto do sistema)
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(datefmt="%Y/%m/%d %H:%M:%S",
                        format="%(asctime)s %(levelname)s %(message)s",
                        level=logging.INFO)

    # run
    sys.exit(main())

# < the end >──────────────────────────────────────────────────────────────────────────
