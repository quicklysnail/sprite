# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 20:50'

import logging

from sprite.settings import Settings


def get_logger(name: str = "sprite"):
    return logging.getLogger(name)


def set_logger(settings: Settings):
    file_path = settings.get("LOG_FILE_PATH", "")
    # project_name = settings.get("PROJECT_NAME")
    logging_format = "[%(name)s %(asctime)s %(levelname)s]: "
    # logging_format = "%(name)s [%(asctime)s %(levelname)s %(filename)s]: "
    # logging_format += "%(module)-7s::l%(lineno)d: "
    # logging_format += "%(module)-7s: "
    logging_format += "%(message)s"

    logging.basicConfig(
        filename=file_path,
        format=logging_format,
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.getLogger("asyncio").setLevel(logging.INFO)
    logging.getLogger("websockets").setLevel(logging.INFO)
