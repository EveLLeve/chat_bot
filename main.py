import sys

import aiohttp
from telegram import ReplyKeyboardMarkup
from random import choice

import logging
from telegram.ext import Application, MessageHandler, filters, ConversationHandler, CommandHandler

from data.config import BOT_TOKEN
from data.db_session import global_init, create_session
from data.user import User

logging.basicConfig(filename='logging\\logs.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)

logger = logging.getLogger(__name__)

previous_user_id = {}


async def start(update, context):
    db_sess = create_session()
    username = update.message.from_user.id
    user = db_sess.get(User, username)
    context.user_data['id'] = username
    context.user_data['username'] = update.message.from_user.first_name if update.message.from_user.first_name\
        else update.message.from_user.username
    context.user_data['chat_id'] = update.message.chat_id
    if user:
        markup = [['начать просмотр', 'посмотреть свою анкету']]
        markup = ReplyKeyboardMarkup(markup, one_time_keyboard=True)
        await update.message.reply_text('Вы можете просмотреть анкеты пользователей или свою выберите действие:',
                                        reply_markup=markup)
        return ConversationHandler.END
    await update.message.reply_text('Это бот для создания и просмотра анкет')
    await update.message.reply_text(
        "Укажите имя, которое будет отображаться в анкете")
    return 2


async def response_description(update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "Расскажите о себе")
    return 3


async def response_sex(update, context):
    context.user_data['description'] = update.message.text
    markup = [['Мужской'],
              ['Женский']]
    markup = ReplyKeyboardMarkup(markup, one_time_keyboard=True)
    await update.message.reply_text(
        "Укажите ваш пол", reply_markup=markup)
    return 4


async def response_town(update, context):
    context.user_data['sex'] = True if update.message.text == 'Женский' else False
    await update.message.reply_text(
        'Укажите город, для пропуска вопроса напишите "пропустить"')
    return 5


async def end_anceting(update, context):
    context.user_data['town'] = update.message.text
    db_sess = create_session()
    user = User()
    user.id = context.user_data['id']
    user.chat_id = context.user_data['chat_id']
    user.username = context.user_data['username']
    user.name = context.user_data['name']
    user.town = context.user_data['town'] if context.user_data['town'].lower() != "пропустить" else ''
    user.sex = context.user_data['sex']
    user.description = context.user_data['description']
    user.url = f'tg://user?id={user.id}'
    db_sess.add(user)
    db_sess.commit()
    await update.message.reply_text("Ваша анкета сохранена")
    markup = [['начать просмотр', 'посмотреть свою анкету']]
    markup = ReplyKeyboardMarkup(markup, one_time_keyboard=True)
    await update.message.reply_text('Вы можете просмотреть анкеты пользователей или свою выберите действие:',
                                    reply_markup=markup)
    return ConversationHandler.END


async def stop(update, context):
    return ConversationHandler.END


async def get_file(update, context, user):
    global previous_user_id
    db_sess = create_session()
    geocoder_api_server = "http://geocode-maps.yandex.ru/1.x/"

    geocoder_params = {
        "apikey": "8013b162-6b42-4997-9691-77b7074026e0",
        "geocode": user.town,
        "format": "json"}

    response = await get_response(geocoder_api_server, geocoder_params)

    if not response:
        sys.exit(1)

    json_response = response
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    toponym_lower = list(map(float, toponym["boundedBy"]["Envelope"]["lowerCorner"].split()))
    toponym_upper = list(map(float, toponym["boundedBy"]["Envelope"]["upperCorner"].split()))
    toponym_coodrinates = toponym["Point"]["pos"]
    toponym_longitude, toponym_lattitude = toponym_coodrinates.split(" ")

    spn = f'spn={str(toponym_upper[0] - toponym_lower[0])},{str(toponym_upper[1] - toponym_lower[1])}'
    ll = f'll={toponym_longitude},{toponym_lattitude}'
    static_api_request = f"https://static-maps.yandex.ru/v1?{ll}&{spn}&apikey=f3a0fe3a-b07e-4840-a1da-06f18b2ddf13"
    previous_user = db_sess.get(User, previous_user_id[user.id])
    await context.bot.send_photo(
        previous_user.chat_id,
        static_api_request
    )


async def get_response(url, params):
    logger.info(f"getting {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            return await resp.json()


async def text(update, context):
    global previous_user_id
    db_sess = create_session()
    user = db_sess.get(User, update.message.from_user.id)
    previous_user = db_sess.get(User, previous_user_id[user.id] if user.id in previous_user_id.keys() else 0)
    texts = update.message.text
    if texts == 'начать просмотр' or texts == 'продолжить просмотр':
        await choicess(user, update, context)
    elif texts == 'посмотреть свою анкету':
        markup = [['вернуться назад']]
        markup = ReplyKeyboardMarkup(markup, one_time_keyboard=True)
        form = user
        desc = f"\nОписание: {form.description}" if form.description else ""
        town = f"\nГород: {form.town}" if form.town else ""
        await update.message.reply_text(f'Имя: {form.name}{desc}{town}\nПол: {form.sex}', reply_markup=markup)
    elif texts == '👍':
        texting = f'<a href="{user.url}"><i><b>{user.username}</b></i></a>'
        await context.bot.send_message(previous_user.chat_id, f'{texting} понравилась ваша анкета',
                                       parse_mode='html')
        user.disliked += f'{", " if user.disliked else ""}{previous_user_id[user.id]}'
        db_sess.commit()
        previous_user.disliked += f'{", " if previous_user.disliked else ""}{user.id}'
        db_sess.commit()
        await choicess(user, update, context)
        if user.town:
            await get_file(update, context, user)
    elif texts == '👎':
        user.disliked += f'{", " if user.disliked else ""}{previous_user_id[user.id]}'
        db_sess.commit()
        previous_user.disliked += f'{", " if previous_user.disliked else ""}{user.id}'
        db_sess.commit()
        await choicess(user, update, context)
    elif texts == 'вернуться назад':
        await start(update, context)


async def choicess(user, update, context):
    global previous_user_id
    markup = [['👍', '👎'],
              ['вернуться назад']]
    markup = ReplyKeyboardMarkup(markup, one_time_keyboard=True)
    db_sess = create_session()
    sp = db_sess.query(User).filter(User.id.not_in([i for i in user.disliked.split(', ')]),
                                    User.id != user.id).all()
    if sp:
        form = choice(sp)
        if form:
            desc = f"\nОписание: {form.description}" if form.description else ""
            town = f"\nГород: {form.town}" if form.town else ""
            await update.message.reply_text(f'Имя: {form.name}{desc}{town}\nПол: {form.sex}',
                                            reply_markup=markup)
            previous_user_id[user.id] = form.id
    else:
        markup = [['продолжить просмотр'],
                  ['вернуться назад']]
        markup = ReplyKeyboardMarkup(markup, one_time_keyboard=True)
        await update.message.reply_text(f'Не осталось анкет, вы можете вернуться позже', reply_markup=markup)


def main():
    global_init('db/forms.sqlite')
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, response_description)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, response_sex)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, response_town)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, end_anceting)]
        },
        fallbacks=[CommandHandler('stop', stop)]
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    application.run_polling()


if __name__ == '__main__':
    main()
