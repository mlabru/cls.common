# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

test_schema
testes do esquema versionado do catalog.db (cls_common.dbase.schema):
banco novo, idempotência, bancos antigos (obs_time, sequences sem preset),
check_schema, transação (rollback) e linha de comando.  Usa nomes de
arquivo próprios: <tmp>/catalog.db já vem migrado (fixture catalog_migrado)

2026.nov  mlabru  initial version: os testes de migração antiga vieram de
                  21.mvol/test_volDBWriter.py e 27.nowcast/test_database.py
"""
# < imports >──────────────────────────────────────────────────────────────────────────

# python library
import sqlite3

# pytest
import pytest

# locals
import cls_common.dbase.schema as sc

# < helpers >──────────────────────────────────────────────────────────────────────────

MT_TABLES = {"volumes", "processing_log", "radar_sites", "vol_raw_observations",
             "cappi_products", "sequences"}

MT_INDEXES = {"idx_timestamp", "idx_status", "idx_radar_timestamp", "idx_sequences_target",
              "idx_products_status", "vol_raw_observations_idx_mtime",
              "vol_raw_observations_idx_timestamp"}

# -------------------------------------------------------------------------------------
def _objects(fs_db: str, fs_type: str) -> set:
    lconn = sqlite3.connect(fs_db)

    try:
        return {lt[0] for lt in lconn.execute(
            "SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%'",
            (fs_type,))}

    finally:
        lconn.close()

def _version(fs_db: str) -> int:
    lconn = sqlite3.connect(fs_db)

    try:
        return sc.schema_version(lconn)

    finally:
        lconn.close()

# < banco novo e idempotência >────────────────────────────────────────────────────────

def test_banco_novo_ganha_todo_o_esquema(tmp_path):
    ls_db = str(tmp_path / "sub" / "novo.db")

    assert (0, sc.CI_SCHEMA_VERSION) == sc.migrate(ls_db)

    assert MT_TABLES == _objects(ls_db, "table") - {"sqlite_sequence"}
    assert MT_INDEXES == _objects(ls_db, "index")
    assert sc.CI_SCHEMA_VERSION == _version(ls_db)

def test_migrar_de_novo_nao_muda_nada(tmp_path):
    ls_db = str(tmp_path / "novo.db")
    sc.migrate(ls_db)

    lconn = sqlite3.connect(ls_db)
    llst_before = lconn.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
    lconn.close()

    assert (sc.CI_SCHEMA_VERSION, sc.CI_SCHEMA_VERSION) == sc.migrate(ls_db)

    lconn = sqlite3.connect(ls_db)
    assert llst_before == lconn.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
    lconn.close()

def test_dry_run_nao_aplica(tmp_path):
    ls_db = str(tmp_path / "novo.db")

    assert (0, 0) == sc.migrate(ls_db, fb_dry_run=True)
    assert 0 == _version(ls_db)
    assert set() == _objects(ls_db, "table")

# < bancos antigos (correções da migração 1) >────────────────────────────────────────

def test_obs_time_vira_timestamp_com_valores_e_indice_novo(tmp_path):
    # base com a coluna no nome anterior (obs_time) e o índice dela
    ls_db = str(tmp_path / "antigo.db")
    lconn = sqlite3.connect(ls_db)
    lconn.execute("CREATE TABLE vol_raw_observations (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                  "fullpath TEXT NOT NULL UNIQUE, mtime REAL NOT NULL, obs_time REAL, "
                  "source TEXT NOT NULL, created_at TEXT)")
    lconn.execute("CREATE INDEX vol_raw_observations_idx_obs_time "
                  "ON vol_raw_observations(obs_time)")
    lconn.execute("INSERT INTO vol_raw_observations (fullpath, mtime, obs_time, source) "
                  "VALUES ('a/b.mvol', 1.0, 1781530822.0, 'mvol')")
    lconn.commit()
    lconn.close()

    sc.migrate(ls_db)

    lconn = sqlite3.connect(ls_db)
    lset_cols = {lt[1] for lt in lconn.execute("PRAGMA table_info(vol_raw_observations)")}
    lset_idx = {lt[1] for lt in lconn.execute("PRAGMA index_list(vol_raw_observations)")}
    li_ts = lconn.execute("SELECT timestamp FROM vol_raw_observations").fetchone()[0]
    lconn.close()

    assert "timestamp" in lset_cols and "obs_time" not in lset_cols
    assert "vol_raw_observations_idx_timestamp" in lset_idx
    assert "vol_raw_observations_idx_obs_time" not in lset_idx
    assert 1781530822 == li_ts

def test_observacoes_sem_timestamp_ganham_a_coluna(tmp_path):
    # base anterior a obs_time/timestamp: linha antiga fica com timestamp NULL
    ls_db = str(tmp_path / "antigo.db")
    lconn = sqlite3.connect(ls_db)
    lconn.execute("CREATE TABLE vol_raw_observations (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                  "fullpath TEXT NOT NULL UNIQUE, mtime REAL NOT NULL, "
                  "source TEXT NOT NULL, created_at TEXT)")
    lconn.execute("INSERT INTO vol_raw_observations (fullpath, mtime, source) "
                  "VALUES ('a/b.mvol', 1.0, 'monrad')")
    lconn.commit()
    lconn.close()

    sc.migrate(ls_db)

    lconn = sqlite3.connect(ls_db)
    assert [("a/b.mvol", 1.0, None, "monrad")] == lconn.execute(
        "SELECT fullpath, mtime, timestamp, source FROM vol_raw_observations").fetchall()
    lconn.close()

def test_sequences_antigo_ganha_preset(tmp_path):
    # sequences de antes de cappi_products (sem a coluna preset)
    ls_db = str(tmp_path / "antigo.db")
    lconn = sqlite3.connect(ls_db)
    lconn.execute(sc.CS_CREATE_SEQUENCES.replace(",\n    preset     TEXT", ""))
    lconn.execute("INSERT INTO sequences (radar, alcance, input_1, input_2, input_3, "
                  "input_4, target) VALUES ('CGU', 250, 1, 2, 3, 4, 5)")
    lconn.commit()
    lconn.close()

    sc.migrate(ls_db)

    lconn = sqlite3.connect(ls_db)
    assert [("CGU", None)] == lconn.execute("SELECT radar, preset FROM sequences").fetchall()
    lconn.close()

# < check_schema >─────────────────────────────────────────────────────────────────────

def test_check_schema_aceita_a_versao_do_codigo(tmp_path):
    lconn = sqlite3.connect(tmp_path / "catalog.db")
    sc.check_schema(lconn)
    lconn.close()

def test_check_schema_recusa_banco_nao_migrado(tmp_path):
    lconn = sqlite3.connect(tmp_path / "novo.db")

    with pytest.raises(sc.SchemaVersionError, match="rode: python3 -m cls_common.dbase.schema"):
        sc.check_schema(lconn, "novo.db")

    lconn.close()

def test_check_schema_recusa_banco_mais_novo(tmp_path):
    lconn = sqlite3.connect(tmp_path / "catalog.db")
    lconn.execute(f"PRAGMA user_version = {sc.CI_SCHEMA_VERSION + 1}")

    with pytest.raises(sc.SchemaVersionError, match="atualize o cls.common"):
        sc.check_schema(lconn)

    lconn.close()

def test_erro_de_versao_e_um_erro_de_banco():
    # os "except sqlite3.Error" dos programas a tratam sem traceback
    assert issubclass(sc.SchemaVersionError, sqlite3.Error)

def test_migrate_recusa_banco_mais_novo(tmp_path):
    ls_db = str(tmp_path / "catalog.db")
    lconn = sqlite3.connect(ls_db)
    lconn.execute(f"PRAGMA user_version = {sc.CI_SCHEMA_VERSION + 1}")
    lconn.close()

    with pytest.raises(sc.SchemaVersionError):
        sc.migrate(ls_db)

# < transação >────────────────────────────────────────────────────────────────────────

def test_migracao_que_falha_nao_deixa_nada_pela_metade(tmp_path, monkeypatch):
    # a 2ª migração cria uma tabela e falha: nem ela nem a versão ficam
    def _m002_quebrada(fconn):
        fconn.execute("CREATE TABLE meio_caminho (x INTEGER)")
        raise sqlite3.OperationalError("falha simulada")

    ls_db = str(tmp_path / "catalog.db")
    monkeypatch.setattr(sc, "MT_MIGRATIONS", sc.MT_MIGRATIONS + (_m002_quebrada,))
    monkeypatch.setattr(sc, "CI_SCHEMA_VERSION", len(sc.MT_MIGRATIONS))

    with pytest.raises(sqlite3.OperationalError, match="falha simulada"):
        sc.migrate(ls_db)

    assert sc.CI_SCHEMA_VERSION - 1 == _version(ls_db)
    assert "meio_caminho" not in _objects(ls_db, "table")

# < linha de comando >─────────────────────────────────────────────────────────────────

def test_cli_check_rc(tmp_path):
    assert 0 == sc.main([str(tmp_path / "catalog.db"), "--check"])

    ls_db = str(tmp_path / "novo.db")
    sqlite3.connect(ls_db).close()
    assert 1 == sc.main([ls_db, "--check"])

def test_cli_check_nao_cria_o_arquivo(tmp_path):
    lpth = tmp_path / "nao_existe.db"

    assert 1 == sc.main([str(lpth), "--check"])
    assert not lpth.exists()

def test_cli_migra(tmp_path):
    ls_db = str(tmp_path / "novo.db")

    assert 0 == sc.main([ls_db])
    assert sc.CI_SCHEMA_VERSION == _version(ls_db)

# < the end >──────────────────────────────────────────────────────────────────────────
