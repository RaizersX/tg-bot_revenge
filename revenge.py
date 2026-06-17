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
import asyncio

import random
import json
import logging

router = Router()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def load_questions(file_path: str = "questions.json") -> list:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            questions = json.load(file)
            logger.info(f"Успешно загружено {len(questions)} вопросов из {file_path}")
            return questions
    except FileNotFoundError:
        logger.warning(f"Файл '{file_path}' не найден! Бот будет работать без вопросов.")
        return []
    except json.JSONDecodeError:
        logger.error(f"Ошибка форматирования в файле '{file_path}'. Проверьте синтаксис JSON.")
        return []
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при загрузке вопросов: {e}")
        return []

Qestions_db = load_questions()

def replyKeyboard():
    btn1 = KeyboardButton(text = '🚀 Начать учиться')
    btn2 = KeyboardButton(text = '❓ Помощь')
    markup = ReplyKeyboardMarkup(keyboard=[
            [btn1,],
            [btn2]

        ], resize_keyboard=True
    )
    return markup

def get_level_keyboard():
    """Клавиатура для выбора уровня сложности"""
    keyboard = [
        [InlineKeyboardButton(text="🟢 Уровень 1 (Легко)", callback_data="level_1")],
        [InlineKeyboardButton(text="🟡 Уровень 2 (Средне)", callback_data="level_2")],
        [InlineKeyboardButton(text="🔴 Уровень 3 (Сложно)", callback_data="level_3")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command('start'))
@router.message(F.text.lower() == 'старт')
async def start(message: Message):
    await message.answer("""Привет! Я - Фибик🤖 и я помогу тебе с освоением программирования по теоритической части. 
                         Просто скажи,что мне сделать?""",
                        reply_markup=replyKeyboard())

@router.message(Command('help'))
@router.message(F.text.lower() == 'помощь')
async def help(message: Message):
    await message.answer('Список команд:\n'
                         'Напишите "старт" или выполните команду /start , чтобы перезапустить меня\n'
                         '...')

