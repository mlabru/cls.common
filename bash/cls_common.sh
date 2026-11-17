# Centro Logístico de Simulação Meteorológica
# Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo
#
# cls_common.sh
# funções bash comuns aos projetos cls (19.dash, 21.mrad, 21.mvol, 23.blitz,
# 23.goes, 25.oflow, 25.u-net, 27.nowcast): rotação simples de log, logger
# com timestamp UTC e a trava do ambiente de teste (CLS_ENV=test,
# cls.test).
#
# mora no repo cls.common (cls.common/bash/cls_common.sh).  Cada projeto o
# importa, no seu <pfx>_cfg.sh/<pfx>_common.sh, de CLS_LIB (diretório deste
# arquivo), definida no cls.env da instalação (CLS_ENV_FILE, padrão
# ~/.config/cls/cls.env; modelo em cls.common/etc/cls.env.example).  CLS_LIB
# é obrigatória: não há mais symlink de reserva na raiz dos repos.
# Também põe o pacote Python comum (CLS_PYLIB) no PYTHONPATH
# (cls_setup_pythonpath).
# Alterar este arquivo afeta todos esses projetos: rode as suítes deles.
#
# Só define funções: nada roda no source, e importar duas vezes é inócuo.
# Sem "set -e": herda as opções de shell de quem importa -- por isso nada
# aqui pode falhar à toa (ver check_log_size).
#
# 2026.nov  mlabru  cls_setup_pythonpath: pacote Python comum (cls_common) por
#                   CLS_PYLIB, no lugar dos symlinks apps/{dbase,radar,util}
#
# 2026.nov  mlabru  - prefixo met -> cls: met_log -> cls_log,
#                     met_check_test_env -> cls_check_test_env,
#                     MET_ENV/MET_TST_ROOT -> CLS_ENV/CLS_TST_ROOT.  Durante a
#                     transição a trava ainda aceita MET_ENV/MET_TST_ROOT
#                     (com aviso): um env.sh antigo com MET_ENV=test não
#                     pode desligá-la em silêncio
#                   - localização só por CLS_LIB (cls.env): o symlink
#                     cls_common.sh saiu da raiz dos repos
#
# 2026.nov  mlabru  - check_log_size tolera rotação simultânea: dois
#                     processos do mesmo projeto (jobs paralelos, cron
#                     sobreposto) rotacionando o mesmo log faziam o "mv" (ou
#                     o "stat") do segundo falhar, e sob "set -e" isso
#                     derrubava o chamador dentro de um simples log
#                   - cabeçalho: lista de projetos e caminho do symlink
#                     (o arquivo saiu de 04.dvl/bash para o repo cls.common)
#
# 2026.out  mlabru  initial version: unifica o check_log_size/log() e a trava
#                   CLS_ENV=test, que tinham uma cópia em cada projeto.  As
#                   cópias do 21.mvol e do 21.mrad não usavam realpath -m, e
#                   um caminho com ".." escapava de CLS_TST_ROOT; o log() do
#                   mvol/mrad/oflow era em hora local (agora UTC, como os
#                   logs Python e o contrato "tudo é UTC")

# depends on: bash, coreutils (date, realpath, stat, tee)

# < check_log_size >-------------------------------------------------------------------
#
# rotação simples de log: para cada arquivo informado, se ele existir e for
# maior que GI_LOG_MAX_SIZE (do <pfx>_cfg.sh; padrão 10MB), renomeia para
# ".old" (substituindo o anterior) e recria vazio.
#
# nunca falha: outro processo pode rotacionar o mesmo arquivo entre o teste
# e o "mv" (o arquivo some), e uma falha aqui derrubaria quem só queria
# escrever um log sob "set -e".  Quem perdeu a corrida simplesmente não
# rotaciona: o outro já o fez
#
# uso: check_log_size <arquivo_de_log> [arquivo_de_log...]
#
check_log_size() {

    # for all logs...
    local ls_log_file li_size

    for ls_log_file in "$@"; do
        # tamanho (0 se o arquivo não existe ou sumiu agora)
        li_size="$(stat -c%s "${ls_log_file}" 2>/dev/null || echo 0)"

        # dentro do limite ?
        [ "${li_size}" -gt "${GI_LOG_MAX_SIZE:-10485760}" ] || continue

        # renomeia; se falhar, outro processo já rotacionou
        mv -f "${ls_log_file}" "${ls_log_file}.old" 2>/dev/null || continue
        # cria o novo (o outro processo pode já tê-lo criado: inócuo)
        : >> "${ls_log_file}" 2>/dev/null || true
    done

    return 0

} # check_log_size

# < cls_log >--------------------------------------------------------------------------
#
# logger com timestamp UTC e rotação: grava em <log_app> (tee, ecoando também
# em stderr) -- o nível ([info]/[warn]/[error]) vem no início da mensagem.
# Cada projeto define o seu log() por cima desta, com os arquivos dele
#
# uso: cls_log <log_app> <log_err> "[info]: mensagem"
#
cls_log() {

    local ls_log_app="$1" ls_log_err="$2"
    shift 2

    # rotate log
    check_log_size "${ls_log_app}" "${ls_log_err}"
    # logger
    echo "[$(date -u '+%F %T')] $*" | tee -a "${ls_log_app}" >&2

} # cls_log

# < cls_check_test_env >---------------------------------------------------------------
#
# trava do ambiente de teste: com CLS_ENV=test, todo caminho informado
# precisa estar estritamente dentro de CLS_TST_ROOT (resolvido com realpath
# -m, então ".." e symlinks não escapam) e o servidor remoto, se informado,
# precisa ser esta máquina.  Sem CLS_ENV=test não faz nada.  Caminho vazio
# é ignorado (sobreposição não definida)
#
# opções:
#   -b <base>  diretório-base dos caminhos relativos (padrão: o cwd)
#   -r <ip>    servidor remoto, que precisa ser localhost/127.0.0.1
#
# uso: cls_check_test_env [-b base] [-r ip] <caminho>... || exit 1
#      (retorna 1 com a mensagem em stderr)
#
cls_check_test_env() {

    # transição met -> cls: MET_ENV/MET_TST_ROOT (nomes antigos) ainda
    # valem, para que um env.sh antigo não desligue a trava em silêncio
    if [ -z "${CLS_ENV:-}" ] && [ -n "${MET_ENV:-}" ]; then
        echo "[warn]: MET_ENV está obsoleta; use CLS_ENV" >&2
        CLS_ENV="${MET_ENV}"
    fi

    if [ -z "${CLS_TST_ROOT:-}" ] && [ -n "${MET_TST_ROOT:-}" ]; then
        echo "[warn]: MET_TST_ROOT está obsoleta; use CLS_TST_ROOT" >&2
        CLS_TST_ROOT="${MET_TST_ROOT}"
    fi

    # ambiente de teste ?
    [ "${CLS_ENV:-}" = test ] || return 0

    local ls_base="" ls_remote="" ls_opt OPTIND=1

    while getopts "b:r:" ls_opt; do
        case "${ls_opt}" in
            b) ls_base="${OPTARG}" ;;
            r) ls_remote="${OPTARG}" ;;
            *) echo "[error]: cls_check_test_env: opção inválida" >&2
               return 1 ;;
        esac
    done
    shift $((OPTIND - 1))

    if [ -z "${CLS_TST_ROOT:-}" ]; then
        # logger
        echo "[error]: CLS_ENV=test exige CLS_TST_ROOT" >&2
        # quit fail
        return 1
    fi

    local ls_root ls_path ls_abs
    ls_root="$(realpath -m "${CLS_TST_ROOT}")"

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
            *) echo "[error]: CLS_ENV=test: '${ls_path}' fora de ${CLS_TST_ROOT}" >&2
               # quit fail
               return 1 ;;
        esac
    done

    if [ -n "${ls_remote}" ]; then
        case "${ls_remote}" in
            # localhost ?
            localhost|127.0.0.1) ;;
               # logger
            *) echo "[error]: CLS_ENV=test: servidor '${ls_remote}' não é localhost" >&2
               # quit fail
               return 1 ;;
        esac
    fi

} # cls_check_test_env

# < cls_setup_pythonpath >-------------------------------------------------------------
#
# põe o pacote Python comum (cls_common, em CLS_PYLIB = cls.common/python,
# definida no cls.env) na frente do PYTHONPATH e o exporta.  Os projetos a
# chamam no <pfx>_cfg.sh; os PYTHONPATH="<proj>/apps..." dos scripts devem
# acrescentar o atual (${PYTHONPATH:+:${PYTHONPATH}}), não substituí-lo.
# Idempotente (não repete o caminho)
#
# uso: cls_setup_pythonpath || exit 1
#      (retorna 1 com a mensagem em stderr se CLS_PYLIB não tiver o pacote)
#
cls_setup_pythonpath() {

    if [ ! -r "${CLS_PYLIB:-}/cls_common/__init__.py" ]; then
        # logger
        echo "[error]: CLS_PYLIB='${CLS_PYLIB:-}' sem o pacote cls_common; defina-a no cls.env" >&2
        # quit fail
        return 1
    fi

    case ":${PYTHONPATH:-}:" in
        # já está ?
        *":${CLS_PYLIB}:"*) ;;
        *) PYTHONPATH="${CLS_PYLIB}${PYTHONPATH:+:${PYTHONPATH}}" ;;
    esac

    export PYTHONPATH

} # cls_setup_pythonpath

# < the end >--------------------------------------------------------------------------
