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

Questions_db = load_questions()

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

def get_question_inline_keyboard(options: list):
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(text=option, callback_data=str(i))])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_questions_by_level(level: int) -> list:
    
    return [q for q in Questions_db if q.get("level") == level]

@router.message(Command('start'))
@router.message(F.text.lower() == 'старт')
async def start(message: Message):
    await message.answer("""Привет! Я - Фибик🤖 и я помогу тебе с освоением программирования по теоритической части. 
Просто скажи,что мне сделать?""",
                        reply_markup=replyKeyboard())

@router.message(Command('help'))
@router.message(F.text.func(lambda text: 'помощь' in text.lower()))
async def help(message: Message):
    await message.answer('Список команд:\n'
                         'Напишите "старт" или выполните команду /start , чтобы перезапустить меня\n'
                         '...')
    
@router.message(F.text == '🚀 Начать учиться')
async def start_quiz(message: Message, state: FSMContext):
    if not Questions_db:
        logger.warning(f"Пользователь {message.from_user.id} попытался начать квиз, но база вопросов пуста.")
        await message.answer("Извините, мы пока в разработке((((")
        return


    await state.set_state(QuizState.waiting_for_level)
    logger.info(f"Пользователь {message.from_user.id} перешел к выбору уровня.")
    
    await message.answer(
        "🎯 <b>Выбери уровень сложности:</b>",
        reply_markup=get_level_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(QuizState.waiting_for_level, F.data.startswith("level_"))
async def process_level_selection(callback: CallbackQuery, state: FSMContext):
    level = int(callback.data.split("_")[1]) 
    logger.info(f"Пользователь {callback.from_user.id} выбрал уровень {level}.")
    
    # Сохраняем уровень в состояние
    await state.update_data(current_level=level)
    
    # Фильтруем вопросы по уровню
    available_questions = get_questions_by_level(level)
    
    if not available_questions:
        await callback.message.edit_text(
            f"😔 К сожалению, вопросов для уровня {level} пока нет. Попробуй другой уровень.",
            reply_markup=None
        )
        await state.clear()
        await callback.answer()
        return
        
    question_data = random.choice(available_questions)
    await state.update_data(current_question=question_data)
    await state.set_state(QuizState.waiting_for_answer)
    
    await callback.message.edit_text(
        f"📝 <b>Вопрос (Уровень {level}):</b>\n{question_data['question']}",
        reply_markup=get_question_inline_keyboard(question_data['options']),
        parse_mode="HTML"
    )
    await callback.answer()

    
@router.callback_query(QuizState.waiting_for_answer, F.data.isdigit())
async def process_quiz_answer_v2(callback: CallbackQuery, state: FSMContext):
    selected_index = int(callback.data)
    data = await state.get_data()
    current_question = data.get('current_question')
    current_level = data.get('current_level')
    
    if not current_question:
        await callback.answer("Ошибка: вопрос не найден.", show_alert=True)
        return

    correct_index = current_question['correct_index']
    if selected_index == correct_index:
        result_text = "✅ Правильно! Молодец!"
    else:
        correct_answer_text = current_question['options'][correct_index]
        result_text = f"❌ Неверно. Правильный ответ: {correct_answer_text}"
        
    await callback.message.edit_text(
        text=f"{callback.message.text}\n\n{result_text}",
        reply_markup=None
    )
    
    await callback.message.answer(
        "Что дальше?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующий вопрос (этот же уровень)", callback_data="next_question")],
            [InlineKeyboardButton(text="🔄 Сменить уровень", callback_data="change_level")]
        ])
    )

@router.callback_query(F.data == "next_question")
async def next_question_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_level = data.get("current_level")
    
    if not current_level:
        await callback.answer("Сначала выбери уровень через /start", show_alert=True)
        return
        
    available_questions = get_questions_by_level(current_level)
    if not available_questions:
        await callback.answer("Вопросы этого уровня закончились!", show_alert=True)
        return

    question_data = random.choice(available_questions)
    await state.update_data(current_question=question_data)
    await state.set_state(QuizState.waiting_for_answer)
    
    await callback.message.answer(
        f"📝 <b>Новый вопрос (Уровень {current_level}):</b>\n{question_data['question']}",
        reply_markup=get_question_inline_keyboard(question_data['options']),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "change_level")
async def change_level_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(QuizState.waiting_for_level)
    
    await callback.message.edit_text(
        "🎯 <b>Выбери новый уровень сложности:</b>",
        reply_markup=get_level_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()