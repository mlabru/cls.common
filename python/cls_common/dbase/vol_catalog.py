# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

vol_catalog
estrutura de persistência das observações de recepção radar

fullpath é o caminho RELATIVO ao diretório remoto (REMOTE_DIR), no formato
<estação>/<RRR>/<EEE>-<RRR>--<AAAA-MM-DD>--<HH-MM-SS>.mvol, como sai de
find -printf '%P'.  O prefixo do servidor não serve a nenhum consumidor; os
diretórios sim, e a unicidade (UNIQUE) só funciona se todo arquivo for gravado
sempre no mesmo formato (ver check_relpath()).

escritor único: vol_sync.sh (volDBWriter.py, source='mvol').  O monrad
(21.mrad) só lê a tabela, pelo mesmo arquivo via symlink.  Linhas antigas com
source='monrad' são de quando ele também gravava.

2026.nov  mlabru  DDL e ensure_schema() saíram para cls_common.dbase.schema
                  (migração 1); ficam o nome da tabela e check_relpath()
2026.nov  mlabru  movido para o repo cls.common (pacote cls_common): imports
                  cls_common.dbase/radar/util (eram dbase/radar/util por symlink)
2026.out  mlabru  - docstrings: o 21.mvol é o único escritor (o monrad passou a
                    abrir o catalog.db somente leitura)

2026.set  mlabru  - fullpath passa a ser relativo a REMOTE_DIR (antes, o
                    caminho absoluto no servidor); check_relpath(), guarda
                    comum dos escritores
                  - coluna obs_time renomeada para timestamp (INTEGER),
                    mesmo nome/conteúdo de volumes.timestamp;
                    ensure_schema() migra (RENAME COLUMN) e troca o índice
                  - coluna obs_time (epoch UTC extraído do nome do .mvol, o
                    único tempo confiável -- mtime vem do relógio do
                    servidor e fica só como hora de chegada bruta) e
                    ensure_schema(), que migra bases antigas (ALTER TABLE
                    ADD COLUMN)

2026.ago  mlabru  initial version (Linux/Python)
"""
# < constants >────────────────────────────────────────────────────────────────────────

# nome da tabela (prefixo "vol_" para não colidir com as tabelas de outros
# programas no mesmo catalog.db)
CS_TABLE = "vol_raw_observations"

# a DDL da tabela (e as migrações antigas obs_time -> timestamp) mora em
# cls_common.dbase.schema, o esquema versionado do catalog.db

# ─────────────────────────────────────────────────────────────────────────────────────
def check_relpath(fs_path: str) -> None:
    """
    confere que fs_path está no formato de fullpath (relativo a REMOTE_DIR)

    gravar o caminho absoluto (listagem antiga, find sem '%P') duplicaria
    cada arquivo já registrado com o caminho relativo, já que a deduplicação
    é pelo texto de fullpath

    :param fs_path: caminho a gravar

    :raises ValueError: caminho vazio ou absoluto
    """
    if not fs_path:
        raise ValueError("fullpath vazio")

    if fs_path.startswith('/'):
        raise ValueError(f"fullpath absoluto (esperado relativo a REMOTE_DIR): {fs_path}")

# < the end >──────────────────────────────────────────────────────────────────────────
