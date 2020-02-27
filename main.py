import os
import logging
from logger_setup import setup_logger
from bot_controller import BotController


def main():
    setup_logger()
    logging.info('Application started')
    bot = BotController(os.environ["CASTBOT_TOKEN"])
    bot.start_bot()
    bot.idle()


if __name__ == '__main__':
    main()
