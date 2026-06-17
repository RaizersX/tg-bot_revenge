from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from quest import QuizState
from datetime import date, time, datetime
import asyncio
import aiosqlite

router = Router()


def replyKeyboard():
    btn1 = KeyboardButton(text = 'Начать учиться')
    btn2 = KeyboardButton(text = 'Помощь')
    markup = ReplyKeyboardMarkup(keyboard=[
            [btn1,],
            [btn2]

        ], resize_keyboard=True
    )
    return markup

@router.message(Command('start'))
@router.message(F.text.lower() == 'старт')
async def start(message: Message):
    await message.answer("""Привет! Я - Фибик и я помогу тебе с освоением программирования по теоритической части. 
                         Просто скажи,что мне сделать?""",
                        reply_markup=replyKeyboard())

@router.message(Command('help'))
@router.message(F.text.lower() == 'помощь')
async def help(message: Message):
    await message.answer('Список команд:\n'
                         'Напишите "старт" или выполните команду /start , чтобы перезапустить меня\n'
                         '...')

