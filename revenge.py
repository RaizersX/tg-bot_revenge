from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from quest import QuizState, AddQuestionState
import asyncio

import random
import json
import logging
from dotenv import load_dotenv
from os import getenv


load_dotenv()
Admin = getenv("USER_ID", "")
if Admin:
    
    ADMIN_ID = [int(x.strip()) for x in Admin.split(',') if x.strip().isdigit()]
else:
    ADMIN_ID = []

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

def save_questions(questions: list, file_path: str = "questions.json"):
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(questions, file, ensure_ascii=False, indent=2)
        logger.info(f"Успешно сохранено {len(questions)} вопросов в {file_path}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении вопросов: {e}")
        return False

def is_admin(message: Message) -> bool:
    user_id = message.from_user.id
    print(f"DEBUG: ID пользователя из сообщения: {user_id} (тип: {type(user_id)})")
    print(f"DEBUG: Список ADMIN_ID: {ADMIN_ID} (тип элементов: {[type(x) for x in ADMIN_ID]})")
    
    result = user_id in ADMIN_ID
    print(f"DEBUG: Результат проверки: {result}")
    return result

def replyKeyboard(message: Message = None):
    btn1 = KeyboardButton(text = '🚀 Начать учиться')
    btn2 = KeyboardButton(text = '❓ Помощь')

    markup = ReplyKeyboardMarkup(keyboard=[
            [btn1,],
            [btn2]

        ], resize_keyboard=True
    )

    if message and is_admin(message):
        btn_admin = KeyboardButton(text='⚙️ Админ панель')
        markup.keyboard.append([btn_admin])


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
                        reply_markup=replyKeyboard(message))

@router.message(Command('help'))
@router.message(F.text.func(lambda text: 'помощь' in text.lower()))
async def help(message: Message):
    help_text = 'Список команд:\n'
    help_text += 'Напишите "старт" или выполните команду /start , чтобы перезапустить меня\n'
    
    if is_admin(message):
        help_text += '\n🔧 <b>Команды для администратора:</b>\n'
        help_text += '/add_question - Добавить новый вопрос\n'
        help_text += '/view_questions - Посмотреть все вопросы\n'
    
    await message.answer(help_text, parse_mode="HTML")
    
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
        explanation = current_question['explanation']
        correct_answer_text = current_question['options'][correct_index]
        result_text = f"❌ Неверно. Правильный ответ: {correct_answer_text}\nВот почему: {explanation}"
        
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

@router.message(Command('add_question'))
async def start_add_question(message: Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await state.set_state(AddQuestionState.waiting_for_question)
    await message.answer(
        "📝 <b>Добавление нового вопроса</b>\n\n"
        "Шаг 1/5: Введите текст вопроса:",
        parse_mode="HTML"
    )

@router.message(AddQuestionState.waiting_for_question)
async def process_question_text(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    await state.update_data(question_text=message.text)
    await state.set_state(AddQuestionState.waiting_for_options)
    await message.answer(
        "✅ Текст вопроса сохранен.\n\n"
        "Шаг 2/5: Введите варианты ответов (каждый вариант с новой строки).\n"
        "Минимум 2 варианта, максимум 10.\n\n"
        "<b>Пример:</b>\n"
        "Вариант 1\n"
        "Вариант 2\n"
        "Вариант 3",
        parse_mode="HTML"
    )

@router.message(AddQuestionState.waiting_for_options)
async def process_options(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    options = [opt.strip() for opt in message.text.split('\n') if opt.strip()]
    if len(options) < 2:
        await message.answer("❌ Нужно минимум 2 варианта ответа. Попробуйте снова:")
        return
    
    if len(options) > 10:
        await message.answer("❌ Максимум 10 вариантов ответа. Попробуйте снова:")
        return
    
    await state.update_data(options=options)
    await state.set_state(AddQuestionState.waiting_for_correct_index)
    
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    await message.answer(
        "✅ Варианты сохранены.\n\n"
        f"<b>Ваши варианты:</b>\n{options_text}\n\n"
        "Шаг 3/5: Введите номер правильного ответа (1, 2, 3...):",
        parse_mode="HTML"
    )

@router.message(AddQuestionState.waiting_for_correct_index)
async def process_correct_index(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    try:
        correct_index = int(message.text) - 1
        data = await state.get_data()
        options = data.get('options', [])
        
        if correct_index < 0 or correct_index >= len(options):
            await message.answer(f"❌ Номер должен быть от 1 до {len(options)}. Попробуйте снова:")
            return
        
        await state.update_data(correct_index=correct_index)
        await state.set_state(AddQuestionState.waiting_for_explanation)
        await message.answer(
            "✅ Правильный ответ сохранен.\n\n"
            "Шаг 4/5: Введите объяснение правильного ответа "
            "(почему этот ответ верный):",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")

@router.message(AddQuestionState.waiting_for_explanation)
async def process_explanation(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    await state.update_data(explanation=message.text)
    await state.set_state(AddQuestionState.waiting_for_level)
    
    await message.answer(
        "✅ Объяснение сохранено.\n\n"
        "Шаг 5/5: Выберите уровень сложности:\n"
        "1 - Легкий\n"
        "2 - Средний\n"
        "3 - Сложный",
        parse_mode="HTML"
    )

@router.message(AddQuestionState.waiting_for_level)
async def process_level(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    try:
        level = int(message.text)
        if level not in [1, 2, 3]:
            await message.answer("❌ Уровень должен быть 1, 2 или 3. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("❌ Введите число (1, 2 или 3). Попробуйте снова:")
        return
    
    data = await state.get_data()
    new_question = {
        "question": data.get('question_text'),
        "options": data.get('options'),
        "correct_index": data.get('correct_index'),
        "explanation": data.get('explanation'),
        "level": level
    }
    
    # Добавляем вопрос в базу
    Questions_db.append(new_question)
    
    # Сохраняем в файл
    if save_questions(Questions_db):
        await message.answer(
            "✅ <b>Вопрос успешно добавлен!</b>\n\n"
            f"<b>Вопрос:</b> {new_question['question']}\n"
            f"<b>Уровень:</b> {level}\n"
            f"<b>Вариантов:</b> {len(new_question['options'])}\n\n"
            "Теперь этот вопрос доступен для викторины.",
            parse_mode="HTML",
            reply_markup=replyKeyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при сохранении вопроса в файл. "
            "Вопрос добавлен в память, но может быть потерян при перезапуске.",
            reply_markup=replyKeyboard()
        )
    
    await state.clear()
