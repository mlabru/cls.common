# Centro Logístico de Simulação Meteorológica
# Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo
#
# cls_common.sh
# funções bash comuns aos projetos met (21.mrad, 21.mvol, 27.nowcast,
# 25.oflow): rotação simples de log, logger com timestamp UTC e a trava do
# ambiente de teste (MET_ENV=test, 21.mvol/tst_env).
#
# cada projeto o vê por um symlink na raiz (<projeto>/04.dvl/cls_common.sh ->
# ../../04.dvl/bash/cls_common.sh) e o importa do <pfx>_cfg.sh e/ou do
# <pfx>_common.sh.  Só define funções: nada roda no source, e importar duas
# vezes é inócuo.  Sem "set -e": herda as opções de shell de quem importa.
#
# 2026.out  mlabru  initial version: unifica o check_log_size/log() e a trava
#                   MET_ENV=test, que tinham uma cópia em cada projeto.  As
#                   cópias do 21.mvol e do 21.mrad não usavam realpath -m, e
#                   um caminho com ".." escapava de MET_TST_ROOT; o log() do
#                   mvol/mrad/oflow era em hora local (agora UTC, como os
#                   logs Python e o contrato "tudo é UTC")

# depends on: bash, coreutils (date, realpath, stat, tee)

# < check_log_size >-------------------------------------------------------------------
#
# rotação simples de log: para cada arquivo informado, se ele existir e for
# maior que GI_LOG_MAX_SIZE (do <pfx>_cfg.sh; padrão 10MB), renomeia para
# ".old" e recria vazio
#
# uso: check_log_size <arquivo_de_log> [arquivo_de_log...]
#
check_log_size() {

    # for all logs...
    local ls_log_file

    for ls_log_file in "$@"; do
        # se o arquivo de log existir e for maior que o limite
        if [ -f "${ls_log_file}" ] && \
           [ "$(stat -c%s "${ls_log_file}")" -gt "${GI_LOG_MAX_SIZE:-10485760}" ]; then
            # renomeia
            mv "${ls_log_file}" "${ls_log_file}.old"
            # cria o novo
            touch "${ls_log_file}"
        fi
    done

} # check_log_size

# < met_log >--------------------------------------------------------------------------
#
# logger com timestamp UTC e rotação: grava em <log_app> (tee, ecoando também
# em stderr) -- o nível ([info]/[warn]/[error]) vem no início da mensagem.
# Cada projeto define o seu log() por cima desta, com os arquivos dele
#
# uso: met_log <log_app> <log_err> "[info]: mensagem"
#
met_log() {

    local ls_log_app="$1" ls_log_err="$2"
    shift 2

    # rotate log
    check_log_size "${ls_log_app}" "${ls_log_err}"
    # logger
    echo "[$(date -u '+%F %T')] $*" | tee -a "${ls_log_app}" >&2

} # met_log

# < met_check_test_env >---------------------------------------------------------------
#
# trava do ambiente de teste: com MET_ENV=test, todo caminho informado
# precisa estar estritamente dentro de MET_TST_ROOT (resolvido com realpath
# -m, então ".." e symlinks não escapam) e o servidor remoto, se informado,
# precisa ser esta máquina.  Sem MET_ENV=test não faz nada.  Caminho vazio
# é ignorado (sobreposição não definida)
#
# opções:
#   -b <base>  diretório-base dos caminhos relativos (padrão: o cwd)
#   -r <ip>    servidor remoto, que precisa ser localhost/127.0.0.1
#
# uso: met_check_test_env [-b base] [-r ip] <caminho>... || exit 1
#      (retorna 1 com a mensagem em stderr)
#
met_check_test_env() {

    # ambiente de teste ?
    [ "${MET_ENV:-}" = test ] || return 0

    local ls_base="" ls_remote="" ls_opt OPTIND=1

    while getopts "b:r:" ls_opt; do
        case "${ls_opt}" in
            b) ls_base="${OPTARG}" ;;
            r) ls_remote="${OPTARG}" ;;
            *) echo "[error]: met_check_test_env: opção inválida" >&2
               return 1 ;;
        esac
    done
    shift $((OPTIND - 1))

    if [ -z "${MET_TST_ROOT:-}" ]; then
        # logger
        echo "[error]: MET_ENV=test exige MET_TST_ROOT" >&2
        # quit fail
        return 1
    fi

    local ls_root ls_path ls_abs
    ls_root="$(realpath -m "${MET_TST_ROOT}")"

    # for all paths...
    for ls_path in "$@"; do
        # sobreposição não definida ?
        [ -n "${ls_path}" ] || continue

        # relativo à base, que pode ainda não existir (máquina nova)
        case "${ls_path}" in
            /*) ls_abs="${ls_path}" ;;
            *)  ls_abs="${ls_base:+${ls_base}/}${ls_path}" ;;
        esac

        case "$(realpath -m "${ls_abs}")" in
            # dentro da raiz de teste ?
            "${ls_root}"/*) ;;
               # logger
            *) echo "[error]: MET_ENV=test: '${ls_path}' fora de ${MET_TST_ROOT}" >&2
               # quit fail
               return 1 ;;
        esac
    done

    if [ -n "${ls_remote}" ]; then
        case "${ls_remote}" in
            # localhost ?
            localhost|127.0.0.1) ;;
               # logger
            *) echo "[error]: MET_ENV=test: servidor '${ls_remote}' não é localhost" >&2
               # quit fail
               return 1 ;;
        esac
    fi

} # met_check_test_env

# < the end >--------------------------------------------------------------------------
