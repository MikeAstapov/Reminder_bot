import asyncio
import datetime
import logging
import os
from random import random

import aioschedule
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from aiogram_calendar import simple_cal_callback, SimpleCalendar

import remember_list
from bot_buttons import buttons
from classes import Promises
from config import token
from database import db_admin
from mail_sendler import send_email

bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())
now = datetime.datetime.now()


def main():
    path = "logs"
    logging.basicConfig(filename=os.path.join(path, f'{now.strftime("%d-%m-%Y")}.txt'), filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S', encoding='UTF-8', level=logging.DEBUG)
    logging.info("!!СТАРТ ЛОГА!!!")

    db_admin.sql_start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    """Команда /start используется для начала работы с ботом.

    Приветствует нового пользователя и предлагает создать обещание.
    Если он уже зарегистрирован в базе данных = напоминает ему о данном обещании"""
    if db_admin.check_user(message.from_user.id) != None:
        await message.answer("Опять ты ? \n"
                             "Нажми кнопку, чтобы узнать что ты обещал:  ", reply_markup=buttons.check_promise_button)

    else:
        await message.answer(f"Привет {message.from_user.full_name}.\n"
                             f"Я бот напоминалка.Оставь мне обещание,и я буду о нем напоминать",
                             reply_markup=buttons.promise_button)


@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    """Стандартная функция HELP с кратким описанием принципа работы с ботом
    :rtype:
    """
    await message.answer("Оставь обещание и я буду о нем напоминать. Используй клавиатуру для выбора")


@dp.message_handler(text='Дать обещание')
async def promise(message: types.Message):
    """Функция для работы с FSM состоянием.

            Запрашивает у пользователя текст обещания и сохраняет его в памяти"""

    await Promises.promis_text.set()
    await message.answer("Хорошо.Напиши что ты хочешь пообещать", reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Promises.promis_text)
async def answer_text(message: types.Message, state: FSMContext):
    """Функция охраняет данный пользователем ответ в data для дальнейшей записи в БД,
    а также запрашивает ввод даты для дедлайна выводя календарь для выбора
    FMS состояние сбрасывается(с сохранением предыдущих ответов) для возможности запуска и выбора даты календаря"""
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    async with state.proxy() as data:
        data["user_id"] = user_id
        data["user_name"] = user_name
        data["promise"] = message.text
        await message.delete()

    await state.reset_state(with_data=False)
    await message.answer("Хорошо.Теперь введи дату дедлайна", reply_markup=await SimpleCalendar().start_calendar())


@dp.callback_query_handler(simple_cal_callback.filter())
async def answer_date(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """Функция позволяет выбрать дату из календаря, а после сохраняет её в FSM состояние.

    FSM записывается в data , и все данные ( в т.ч. предыдущие ответы пользователя ) записываются в БД"""
    selected, date = await SimpleCalendar().process_selection(call, callback_data)
    if selected:
        await Promises.promis_date.set()
        await state.update_data(deadline=f'{date.strftime("%Y.%m.%d")}')
        data = await state.get_data()
        await db_admin.sql_add(data)
        await state.finish()
        if db_admin.sql_deadline(call.from_user.id)[0] < now.strftime("%Y.%m.%d"):
            await bot.send_message(call.from_user.id, "Вы выбрали уже прошедшее время.Обещание не было создано")
            db_admin.sql_delete(call.from_user.id)
        else:
            await bot.send_message(call.from_user.id, f'Ты пообещал {data["promise"]} до {data["deadline"]}')
            await bot.send_message(call.from_user.id, "Но кому ты даешь это обещание ?",
                                   reply_markup=buttons.promise_email)


@dp.message_handler(text="Себе")
async def answer_sebe(message: types.Message):
    await message.answer("Ок.Буду переодически тебе напоминать об этом", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Просто введи /start ,  для дальнейшего общения со мной")


@dp.message_handler(text="Другому человеку")
async def answer_another(message: types.Message):
    await message.answer("Тогда введите его email адрес", reply_markup=types.ReplyKeyboardRemove())
    await Promises.promis_email.set()


@dp.message_handler(state=Promises.promis_email)
async def answer_email(message: types.Message, state: FSMContext):
    """Функция для сохранения email'а пользователя в БД ,если он выбрал соответствующий пункт меню с ТГ-клавиатуры"""
    async with state.proxy() as data:
        data['email'] = message.text
        if "@" not in message.text:
            await message.answer("Введите адрес почты в верном формате (lohpidor@mail.ru)")
            await Promises.promis_email.set()
        else:
            await db_admin.sql_add_email(data, message.from_user.id)
            await state.finish()
            await message.answer(
                f"Почта записана.Если ты не выполнишь своё обещание до {db_admin.deadline_check(message.from_user.id)[1]} человеку придет письмо"
                f" с рассказом о том, как ты его обманул и не выполнил обещанного.")
            await message.answer("Просто введи /start ,  для дальнейшего общения со мной")


@dp.message_handler(text="Проверить обещание")
async def check_promise(message: types.Message):
    """Проверка данного обещания , через запрос из БД"""
    db_admin.deadline_check(message.from_user.id)
    await message.answer(
        f"Ты обещал {db_admin.check_promise(message.from_user.id)[0]} до {db_admin.deadline_check(message.from_user.id)[1]}")
    await message.answer("Ты выполнил это обещание?", reply_markup=buttons.promise_answer_button)


@dp.message_handler(text="Выполнил")
async def answer_yes(message: types.Message):
    await message.answer("Значит можно удалять ?", reply_markup=buttons.delete_promise_button)
    db_admin.sql_delete(message.from_user.id)


@dp.message_handler(text="Удалить обещание")
async def delete_promise(message: types.Message):
    """Удаление всех данных о пользователе из БД"""
    await message.answer("Обещание удалено."
                         "Можете оставлять новое.\n"
                         "Для этого снова запустите бота командой /start или с помощью menu",
                         reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(text="Еще нет")
async def answer_no(message: types.Message):
    await bot.send_photo(message.from_user.id, "https://raritem.ru/wp-content/uploads/2021/12/thing.jpg",
                         reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['sendall'])
async def sendall(message: types.Message):
    """Функция для ручной отправки напоминания ,всем пользователя из БД"""
    if message.from_user.id == 293427068:
        text = random.choice(remember_list.spisok)
        users = db_admin.all_users()
        for user in users:
            await bot.send_message(user[0], text)
            print(f"Сообщение юзеру {user[1]} (id = {user[0]}) доставлено")


@dp.message_handler(commands=['spam'])
async def spam(message):
    """Функция для проверки БД на дату дедлайна и отправки напоминания или угрозы пользователям в автоматическом режиме"""
    for deadline in db_admin.check_info():
        if deadline[1] <= now.strftime("%Y.%m.%d"):
            await bot.send_message(deadline[0],
                                   "Время вышло и ты не выполнил обещание.Отныне ты официально чорт.Поздравляем  🥳 🥳  🥳  ")
            for mail in db_admin.check_email():
                if mail[0] is not None:
                    await send_email(f"{mail[0]}")
                db_admin.sql_delete(deadline[0])


        else:
            text = random.choice(remember_list.spisok)
            await bot.send_message(deadline[0], text)
            print(f"Сообщение юзеру {deadline[0]} доставлено в {now.strftime('%H:%M  %d.%m.%Y')}!")


@dp.message_handler()
async def command_not_found(message: types.Message):
    await message.answer(f"Команда {message.text} не найдена")
    await message.delete()


@dp.message_handler(content_types='sticker')
async def message_with_sticker(message: types.Message):
    await message.answer('Стикер ? \n'
                         'Всё ясно.Автору 10 лет')


async def scheduler():
    """Таска для автоматической, ежедневной проверки обещаний и дедлайнов"""
    aioschedule.every().day.at("13:00").do(spam, "message")
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(10)


async def on_startup(_):
    asyncio.create_task(scheduler())


if __name__ == '__main__':
    main()
