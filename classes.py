from aiogram.dispatcher.filters.state import StatesGroup, State


class Promises(StatesGroup):
    promis_text = State()
    promis_date = State()
    promis_email = State()