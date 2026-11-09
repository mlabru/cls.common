# -*- coding: utf-8 -*-
"""
opm_logs

2025.mar  mlabru  initial version (Linux/Python)
"""
# < imports >--------------------------------------------------------------------------

# python library
import datetime
import logging
import os

# local
import util.utl_defs as df

# < logging >--------------------------------------------------------------------------

# error logger
M_LOG_ERR = None

# -------------------------------------------------------------------------------------
def logger_check():
    """
    check if the error log can be removed
    
    :returns: none
    """
    # error log handler
    l_handler = M_LOG_ERR.handlers[0]

    # logger filename
    ls_error_fn = l_handler.baseFilename

    # remove log if empty
    logger_remove_empty(ls_error_fn)

# -------------------------------------------------------------------------------------
def logger_init(fs_app_fn: str):
    """
    se não houver erro, remover o arquivo de erro

    :param fs_log_fn (str): log file name

    :returns: error logger
    """
    # timestamp
    l_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # gera nome de log de erro
    ls_error_log = f"{fs_app_fn}_{l_timestamp}.err"

    # return
    return logger_setup(fs_app_fn, ls_error_log)

# -------------------------------------------------------------------------------------
def logger_remove_empty(fs_error_fn: str = "error.err"):
    """
    remove error log if file is empty

    :returns: none
    """
    # error doesn't exists ?
    if os.path.exists(fs_error_fn) and 0 == os.path.getsize(fs_error_fn):
        # logger
        logging.info("no error occurred. File %s will be removed.\n", fs_error_fn)

        # remove error log
        try:
            os.remove(fs_error_fn)

        except: 
            # logger
            logging.info("fail to remove error log %s", fs_error_fn)

# -------------------------------------------------------------------------------------
def logger_setup(fs_app_fn: str = "app", fs_error_fn: str = "error.err"):
    """
    setup logging attributes

    :param fs_app_fn (str): app log file name
    :param fs_error_fn (str): error log file name

    :returns: error logger
    """
    # logger message format
    ls_format = "%(asctime)s - %(levelname)s - %(message)s"

    # logger formatter
    l_formatter = logging.Formatter(ls_format)

    # configuração do logger para mensagens normais
    logging.basicConfig(
        datefmt="%Y/%m/%d %H:%M",
        filename=f"{fs_app_fn}.log",
        level=df.DI_LOG_LEVEL,
        format=ls_format
    )

    # disable logging
    # logging.disable(sys.maxsize)

    # logger error handler
    l_error_handler = logging.FileHandler(fs_error_fn)
    l_error_handler.setLevel(logging.ERROR)
    l_error_handler.setFormatter(l_formatter)

    # logger específico para erros
    l_error_logger = logging.getLogger("error_logger")
    l_error_logger.addHandler(l_error_handler)
    
    # return
    return l_error_logger

# < the end >--------------------------------------------------------------------------
