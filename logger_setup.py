import logging
import os
import yaml
from logging.handlers import RotatingFileHandler
from logging import config


class RotatingFilePathHandler(RotatingFileHandler):
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None, delay=False):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        RotatingFileHandler.__init__(self, filename, mode, maxBytes, backupCount, encoding, delay)


def setup_logging(path='logging_config.yaml', default_level=logging.INFO):
    if os.path.exists(path):
        with open(path) as f:
            try:
                log_config = yaml.safe_load(f.read())
                logging.config.dictConfig(log_config)
                return
            except Exception as e:
                print(e)

    logging.basicConfig(level=default_level,
                        format='%(filename)s: '
                               '%(levelname)s: '
                               '%(funcName)s(): '
                               '%(lineno)d:\t'
                               '%(message)s')
    print('Failed to load configuration file. Using default configs')
