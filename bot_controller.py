import logging

from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton
from yandex_music import Client
from player_controller import PlayerController

proxy = {
    'proxy_url': 'socks5://127.0.0.1:9050',
    'read_timeout': 26, 'connect_timeout': 27
}


class BotController:
    def __init__(self, token):
        self.player_controller = PlayerController()
        self.updater = Updater(token, request_kwargs=proxy, use_context=True)
        self.client = Client(fetch_account_status=False)
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(CommandHandler("start", self._start_callback))
        dispatcher.add_handler(CommandHandler("device", self._select_device_callback))
        dispatcher.add_handler(CommandHandler("control", self._show_controls))
        dispatcher.add_handler(CommandHandler("playlist", self._show_playlist))
        dispatcher.add_handler(CallbackQueryHandler(self._device_query, pattern='device.*'))
        dispatcher.add_handler(CallbackQueryHandler(self._playback_control_query, pattern='playbackControl.*'))
        dispatcher.add_handler(MessageHandler(Filters.text, self._message_callback))
        job_q = self.updater.job_queue
        job_q.run_repeating(self._update_devices, 60*5, first=1)

    def _update_devices(self, context: CallbackContext):
        logging.debug("Updating chromecasts list")
        self.player_controller.update_chromecast_list()

    def _show_playlist(self, update: Update, context: CallbackContext):
        playlist_str = self.player_controller.format_playlist()
        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id,
                                 text=playlist_str)

    def _show_controls(self, update: Update, context: CallbackContext):
        button_list = [[
            InlineKeyboardButton('⏯️', callback_data='playbackControl playpause'),
            InlineKeyboardButton('⏹️', callback_data='playbackControl stop'),
            InlineKeyboardButton('🔊', callback_data='playbackControl volume_up'),
            InlineKeyboardButton('🔉', callback_data='playbackControl volume_down'),
            # TODO: repeat regressed, fix
            # InlineKeyboardButton('🔁', callback_data='playbackControl repeat')
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id,
                                 text="Панель управления",
                                 reply_markup=reply_markup)

    def _get_track_info(self, track_url):
        album_id, track_id = track_url.split('/')[4:7:2]
        track = self.client.tracks(f"{track_id}:{album_id}")[0]
        friendly_name = f'{track.artists[0].name} - {track.title}'
        url = None
        for info in track.get_download_info():
            if info.codec == 'mp3':
                url = info.get_direct_link()
                break
        return url, friendly_name, track.duration_ms

    def _message_callback(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        data = update.message.text
        # TODO delayed url get
        track_info = self._get_track_info(data)
        logging.info("added %s", track_info)
        self.player_controller.push(track_info)
        context.bot.send_message(chat_id=chat_id, text="Трек добавлен")

    def _start_callback(self, update: Update, context: CallbackContext):
        update.message.reply_text('Привет!\nВыбери колонки командой /device'
                                  '\nи отправляй ссылку на трек в Яндекс.Музыке🎵')

    def _select_device_callback(self, update: Update, context: CallbackContext):
        chat_id = update.message.chat_id
        button_list = [[InlineKeyboardButton(cc.device.friendly_name, callback_data=f'device {i}') for i, cc in
                        enumerate(self.player_controller.cached_chromecasts)]]
        reply_markup = InlineKeyboardMarkup(button_list)
        context.bot.send_message(chat_id,
                                 text=f"Найдено {len(self.player_controller.cached_chromecasts)} проигрывателя!\n"
                                      f"Выберите:",
                                 reply_markup=reply_markup)

    def _device_query(self, update: Update, context: CallbackContext):
        data = update.callback_query.data
        idx = int(data.split(' ')[1])
        self.player_controller.select(idx)

    def _playback_control_query(self, update: Update, context: CallbackContext):
        data = update.callback_query.data
        logging.info('playback_control_query: %s', data)
        command = data.split(' ')[1]
        if command == 'playpause':
            self.player_controller.playpause()
        if command == 'stop':
            self.player_controller.stop()
        if command == 'volume_up':
            self.player_controller.volume_up()
        if command == 'volume_down':
            self.player_controller.volume_down()
        if command == 'repeat':
            self.player_controller.repeat()

    def start_bot(self):
        self.updater.start_polling()

    def idle(self):
        self.updater.idle()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(filename)s: '
                               '%(levelname)s: '
                               '%(funcName)s(): '
                               '%(lineno)d:\t'
                               '%(message)s')


    class MockController:
        def __init__(self):
            self.client = Client()

        _get_track_info = BotController._get_track_info


    ctr = MockController()
    info = ctr._get_track_info('https://music.yandex.com/album/4172931/track/32947997')
    assert 'Ed Sheeran - Shape of You' == info[1]
    pass
