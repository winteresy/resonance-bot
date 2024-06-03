
import os
import random
import csv
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FOLDER = os.path.join(BASE_DIR, 'music')
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
DATA_FILE = os.path.join(DATA_FOLDER, 'data.csv')

os.makedirs(DATA_FOLDER, exist_ok=True)

user_data = {}


def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username if update.message.from_user.username else user_id
    user_data[user_id] = {'last_tracks': [], 'location': None, 'activity': None, 'track_message_id': None,
                          'button_message_id': None, 'username': username, 'state': 'awaiting_name'}

    update.message.reply_text('Привет, это бот <b>Resonance</b>, мы создаём генеративную музыку для прогулок и медитаций в городе. ✨💫\nСкоро у нас будет доступно мобильное приложение, а пока вы можете быть в числе первых и протестировать его в telegram! ✈️', parse_mode="html")
    update.message.reply_text('Давайте для начала познакомимся 👀\nНапишите своё имя:')


def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    state = user_data[user_id].get('state', '')

    if state == 'awaiting_name':
        handle_name(update, context)
    elif state == 'awaiting_location':
        handle_location(update, context)
    elif state == 'awaiting_activity':
        handle_activity(update, context)
    else:
        update.message.reply_text('Я не понимаю это сообщение. Пожалуйста, нажми "Следующий трек" для продолжения.')


def handle_name(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    name = update.message.text
    user_data[user_id]['name'] = name
    user_data[user_id]['state'] = 'awaiting_menu'

    # Отправка сообщения-меню
    send_menu(update, context, f'Приятно познакомиться, {name}! 🫶\nНаш бот создан с целью подбора музыки для определенных локаций и действий 🎶')


def send_menu(update: Update, context: CallbackContext, text: str) -> None:
    keyboard = [
        [InlineKeyboardButton("Начать", callback_data='start')],
        [InlineKeyboardButton("О проекте", callback_data='about')],
        [InlineKeyboardButton("Поддержать проект", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text, reply_markup=reply_markup)


def handle_location(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    location = update.message.text
    user_data[user_id]['location'] = location
    user_data[user_id]['state'] = 'ready'  # Изменено состояние на 'ready'

    # Убираем вопрос про действие пользователя и сразу предлагаем погрузиться в резонанс
    send_next_track_button(update, context)


def handle_activity(update: Update, context: CallbackContext) -> None:
    # Удаляем эту функцию, так как она больше не нужна
    pass


def send_next_track_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = update.effective_chat.id

    if user_id in user_data and user_data[user_id]['button_message_id']:
        try:
            context.bot.delete_message(chat_id=user_id, message_id=user_data[user_id]['button_message_id'])
        except Exception as e:
            print(f"Не удалось удалить предыдущее сообщение с кнопками: {e}")

    keyboard = [[InlineKeyboardButton("⏩", callback_data='next_track')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = query.message.reply_text('🌊 Погрузиться в резонанс 🌊', reply_markup=reply_markup)
    user_data[user_id]['button_message_id'] = message.message_id


def send_random_track(update: Update, context: CallbackContext) -> None:
    user_id = update.message.chat_id
    last_tracks = user_data[user_id]['last_tracks']
    available_tracks = [i for i in range(1, 6) if i not in last_tracks]

    if not available_tracks:
        available_tracks = list(range(1, 6))
        last_tracks.clear()

    track_number = random.choice(available_tracks)
    last_tracks.append(track_number)
    if len(last_tracks) > 3:
        last_tracks.pop(0)

    location = user_data[user_id]['location']

    # Сопоставление русских названий с английскими
    location_mapping = {
        'Дом': 'home',
        'Парк': 'park',
        'Город': 'city'
    }

    # Получаем английское название локации
    location_english = location_mapping.get(location)

    if location_english:
        track_path = os.path.join(MUSIC_FOLDER, location_english.lower(), f'{track_number}.mp3')

        if os.path.exists(track_path):
            if user_id in user_data and user_data[user_id]['track_message_id']:
                try:
                    context.bot.delete_message(chat_id=update.message.chat_id,
                                               message_id=user_data[user_id]['track_message_id'])
                except Exception as e:
                    print(f"Не удалось удалить предыдущее голосовое сообщение: {e}")

            with open(track_path, 'rb') as voice_file:
                sent_message = update.message.reply_voice(voice=InputFile(voice_file))

            user_data[user_id]['track_message_id'] = sent_message.message_id

            if user_id in user_data and user_data[user_id]['button_message_id']:
                try:
                    context.bot.delete_message(chat_id=update.message.chat_id,
                                               message_id=user_data[user_id]['button_message_id'])
                except Exception as e:
                    print(f"Не удалось удалить предыдущее сообщение с кнопками: {e}")

            keyboard = [
                [
                    InlineKeyboardButton("👍", callback_data=f'like,{track_number}'),
                    InlineKeyboardButton("👎", callback_data=f'dislike,{track_number}'),
                    InlineKeyboardButton("⏩", callback_data='next_track')
                ],
                [InlineKeyboardButton("Меню", callback_data='menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = update.message.reply_text('🌊 Погрузиться в резонанс 🌊', reply_markup=reply_markup)
            user_data[user_id]['button_message_id'] = message.message_id
        else:
            update.message.reply_text('Трек не найден. Попробуйте снова.')
    else:
        update.message.reply_text(
            'Не удалось определить локацию. Пожалуйста, выберите локацию из предложенных вариантов.')


def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    user_id = query.message.chat.id
    data = query.data.split(',')
    action = data[0]

    if action == 'next_track':
        send_random_track(query, context)

    elif action == 'start':
        user_data[user_id]['state'] = 'awaiting_location'
        keyboard = [
            [InlineKeyboardButton("🏡", callback_data='location,Дом'),
             InlineKeyboardButton("🏙️", callback_data='location,Город'),
             InlineKeyboardButton("🏞️", callback_data='location,Парк')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.reply_text('Где вы сейчас находитесь?', reply_markup=reply_markup)

    elif action == 'about':
        query.message.edit_text(
            'Resonance – MVP-версия будущего приложения для саундскейпинга в пространстве города, о всех возможностях приложения можно прочитать по ссылке: http://resonance-app.tilda.ws \n\nВыберите действие:',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Начать", callback_data='start')],
                [InlineKeyboardButton("Поддержать проект", callback_data='support')]
            ])
        )
    elif action == 'support':
        query.message.edit_text(
            'Чтобы мы продолжали создавать классный контент, можете нас поддержать донатом по ссылке: https://www.tinkoff.ru/cf/8npR27exLyM \n\nВыберите действие:',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Начать", callback_data='start')],
                [InlineKeyboardButton("О проекте", callback_data='about')]
            ])
        )

    elif action == 'menu':
        send_menu(query, context, 'Ну что, погружаемся в Резонанс?')
    elif action == 'location':
        location = data[1]
        user_data[user_id]['location'] = location
        user_data[user_id]['state'] = 'ready'
        name = user_data[user_id]['name']
        query.message.reply_text(f'Отлично, {name}! ✨\nТеперь мы готовы...')
        send_next_track_button(update, context)
    else:
        track_number = int(data[1])
        username = user_data[user_id]['username']
        save_user_feedback(username, track_number, action, user_id)

        if action == 'like':
            new_text = '🔥❤️‍🔥 Погрузиться в резонанс ❤️‍🔥🔥'
        elif action == 'dislike':
            new_text = '❄️🥶 Погрузиться в резонанс 🥶❄️'

        keyboard = [
            [
                InlineKeyboardButton("👍", callback_data=f'like,{track_number}'),
                InlineKeyboardButton("👎", callback_data=f'dislike,{track_number}'),
                InlineKeyboardButton("⏩", callback_data='next_track')
            ],
            [InlineKeyboardButton("Меню", callback_data='menu')]
        ]
        query.edit_message_text(text=new_text, reply_markup=InlineKeyboardMarkup(keyboard))


def save_user_feedback(username, track_number, action, user_id):
    location = user_data[user_id]['location']
    activity = user_data[user_id]['activity']
    with open(DATA_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([username, location, activity, track_number, action])


def main() -> None:
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CallbackQueryHandler(button_callback))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()