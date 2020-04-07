import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
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
        job_q.run_repeating(self._update_devices, 60 * 5, first=1)

    def _update_devices(self, _: CallbackContext):
        logging.debug("Updating chromecasts list")
        self.player_controller.update_chromecast_list()

    def _show_playlist(self, update: Update, context: CallbackContext):
        playlist_str = self.player_controller.format_playlist()

        def trim_msg(msg: str, near_len=400):
            end_pos = msg.find('\n', near_len)
            if end_pos == -1:
                return msg
            return msg[:end_pos] + '\n...'

        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id,
                                 text=trim_msg(playlist_str))

    @staticmethod
    def _show_controls(update: Update, context: CallbackContext):
        button_list = [[
            InlineKeyboardButton('⏯️', callback_data='playbackControl playpause'),
            InlineKeyboardButton('🔊', callback_data='playbackControl volume_up'),
            InlineKeyboardButton('🔉', callback_data='playbackControl volume_down'),
            # TODO: repeat regressed, fix
            # InlineKeyboardButton('🔁', callback_data='playbackControl repeat')
            InlineKeyboardButton('⏭️', callback_data='playbackControl play_next'),
            InlineKeyboardButton('🔀', callback_data='playbackControl shuffle'),
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        chat_id = update.message.chat_id
        context.bot.send_message(chat_id=chat_id,
                                 text="Панель управления",
                                 reply_markup=reply_markup)

    @staticmethod
    def _get_track_info(track):
        friendly_name = f'{track.artists[0].name} - {track.title}'

        def get_url():
            for info in track.get_download_info():
                if info.codec == 'mp3':
                    return info.get_direct_link()

        return get_url, friendly_name, track.duration_ms

    def _add_tracks(self, tracks):
        tracks_info = [self._get_track_info(t) for t in tracks]
        logging.info("added %s", tracks_info)
        self.player_controller.push(tracks_info)

    def process_url(self, data):
        xs = data.split('/')
        if xs[-2] == 'track':
            track = self.client.tracks(f"{xs[6]}:{xs[4]}")[0]
            self._add_tracks([track])
        elif xs[-2] == 'playlists':
            playlist = self.client.users_playlists(xs[6], xs[4])[0]
            track_ids = [t.id for t in playlist.tracks]
            tracks = self.client.tracks(track_ids)
            self._add_tracks(tracks)
        else:
            raise RuntimeError(f"Unparsed data: {data}")

    def _message_callback(self, update: Update, context: CallbackContext):
        data = update.message.text

        self.process_url(data)
        self._show_controls(update, context)

    @staticmethod
    def _start_callback(update: Update, _: CallbackContext):
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

    def _device_query(self, update: Update, _: CallbackContext):
        data = update.callback_query.data
        idx = int(data.split(' ')[1])
        self.player_controller.select(idx)

    def _playback_control_query(self, update: Update, _: CallbackContext):
        data = update.callback_query.data
        logging.info('playback_control_query: %s', data)
        command = data.split(' ')[1]
        if command == 'playpause':
            self.player_controller.playpause()
        elif command == 'volume_up':
            self.player_controller.volume_up()
        elif command == 'volume_down':
            self.player_controller.volume_down()
        # elif command == 'repeat':
        #     self.player_controller.repeat()
        elif command == 'play_next':
            self.player_controller.play_next()
        elif command == 'shuffle':
            self.player_controller.shuffle()

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

    class PCMock:
        def push(self, track_info):
            pass

    class BotControllerMock(BotController):
        # noinspection PyMissingConstructor
        def __init__(self):
            self.player_controller = PCMock()
            self.client = Client()

    ctr = BotControllerMock()
    ctr.process_url('https://music.yandex.com/album/4172931/track/32947997')
    ctr.process_url('https://music.yandex.ru/users/tchernov44le/playlists/1002')
    # ctr._process_url('https://music.yandex.ru/users/tchernov44le/playlists/3')
    # assert 'Ed Sheeran - Shape of You' == info[1]
    pass
