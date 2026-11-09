# -*- coding: utf-8 -*-
"""
Centro Logístico de Simulação Meteorológica
Copyright (c) 1995-2026, Instituto de Controle do Espaço Aéreo

utl_dates
utilitários de conversão de timestamps do pipeline

2026.jan  mlabru  extração da data de um mvol (get_date_from_mvol)
2022.apr  mlabru  initial version (Linux/Python)
"""
# < imports >──────────────────────────────────────────────────────────────────────────

# Python library
from __future__ import annotations

import datetime
import logging
import pathlib
import sys

# < constantes >───────────────────────────────────────────────────────────────────────

# diferença da hora local para GMT (valor absoluto)
CI_DIFF_GMT = 3

# < logging >--------------------------------------------------------------------------

# logger
M_LOG = logging.getLogger(__name__)
M_LOG.setLevel(logging.INFO)

# ─────────────────────────────────────────────────────────────────────────────────────
def datetime_to_timestamp(fdt_date: datetime.datetime) -> int:
    """
    converte datetime para Unix timestamp in seconds

    :param fdt_date: datetime

    :returns: Unix timestamp (naive, UTC implícito)
    """
    # ok
    return int(fdt_date.timestamp())

# ─────────────────────────────────────────────────────────────────────────────────────
def get_date_from_mvol(fs_fname_mvol: str) -> datetime.datetime:
    """
    converte o nome do arquivo mvol em datetime
    ex: 'CGU-250--2025-12-21--02-30-23.mvol'

    :param fs_fname_mvol: path do arquivo mvol

    :returns: datetime
    """
    try:
        # remove a extensão .mvol
        fs_clear_name = pathlib.Path(fs_fname_mvol).stem 
        
        # divide pelas duas -- (separador de metadados vs data)
        # parts[0] = CGU-250, parts[1] = 2025-12-21, parts[2] = 02-30-23
        llst_parts = fs_clear_name.split("--")

        # data & hora        
        ls_data_hora = f"{llst_parts[1]} {llst_parts[2]}"
        
        # ok, converte para datetime
        return datetime.datetime.strptime(ls_data_hora, "%Y-%m-%d %H-%M-%S")

    # em caso de erro,...
    except Exception as l_err:
        # logger
        M_LOG.error(f"data do arquivo {fs_fname_mvol}: {l_err}")
        # quit fail
        return None
        
# -------------------------------------------------------------------------------------
# [datetime.datetime, int]:
def get_date_range(f_args, fi_delta: int, fs_format: str) -> tuple:
    """
    get initial and final dates

    :param f_args: received arguments
    :param fi_delta (int): intervalo de tempo
    :param fs_format (str): string de formato da data

    :returns (tuple): initial date and delta in hours
    """
    # delta
    li_delta = fi_delta

    # no date at all ?
    if ("x" == f_args.dini) and ("x" == f_args.dfnl):
        # datetime object containing current date and time, but 3 hours ahead (GMT)
        ldt_ini = datetime.datetime.now() + datetime.timedelta(hours=CI_DIFF_GMT)

    # just initial date ?
    elif ("x" != f_args.dini) and ("x" == f_args.dfnl):
        # parse initial date
        ldt_ini = parse_date(f_args.dini, fs_format)

        # datetime object containing current date and time, but 3 hours ahead (GMT)
        ldt_fnl = datetime.datetime.now() + datetime.timedelta(hours=CI_DIFF_GMT)
        # build final date
        ldt_fnl = ldt_fnl.replace(minute=0)

        # calculate difference in hours
        ldt_delta = ldt_fnl - ldt_ini
        li_delta = int(ldt_delta.total_seconds() / 3600.)

    # just final date ?
    elif ("x" == f_args.dini) and ("x" != f_args.dfnl):
        # parse final date
        ldt_fnl = parse_date(f_args.dfnl, fs_format)

        # delta
        ldt_ini = ldt_fnl - datetime.timedelta(hours=fi_delta)

    # so, both dates
    else:
        # parse initial date
        ldt_ini = parse_date(f_args.dini, fs_format)

        # parse final date
        ldt_fnl = parse_date(f_args.dfnl, fs_format)

        # calculate difference
        ldt_delta = ldt_fnl - ldt_ini
        li_delta = int(ldt_delta.total_seconds() / 3600.)

    # return initial date and delta in hours
    return ldt_ini.replace(minute=0, second=0, microsecond=0), li_delta

# -------------------------------------------------------------------------------------
def parse_date(fs_date: str, fs_format: str = "%Y-%m-%dT%H:M") -> datetime.datetime:
    """
    parse date

    :param fs_date (str): date to be parsed

    :returns (datetime): date in datetime format
    """
    try:
        # parse data
        ldt_date = datetime.datetime.strptime(fs_date, fs_format)
        # build initial date
        ldt_date = ldt_date.replace(minute=0)

    # em caso de erro,...
    except ValueError as l_err:
        # logger
        M_LOG.error("date format error: %s. Aborting.", l_err)

        # abort
        sys.exit(-1)

    # return date in datetime format
    return ldt_date

# ─────────────────────────────────────────────────────────────────────────────────────
def timestamp_to_datetime(fi_timestamp: int) -> datetime.datetime:
    """
    converte Unix timestamp in seconds para datetime

    :param fi_timestamp: inteiro no formato ts

    :returns: datetime.datetime (naive, UTC implícito)
    """
    # ok
    return datetime.datetime.fromtimestamp(fi_timestamp, tz=datetime.timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────────────
# this is the bootstrap process

if "__main__" == __name__:

    # smoke test
    ldt = timestamp_to_datetime(202506151200)
    assert ldt == datetime.datetime(2025, 6, 15, 12, 0), f"falha: {ldt}"

    li_ts = datetime_to_timestamp(ldt)
    assert li_ts == 202506151200, f"falha: {li_ts}"

    print("utl_dates: OK")

# < the end >──────────────────────────────────────────────────────────────────────────
