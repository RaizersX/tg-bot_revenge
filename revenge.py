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
from open_ans import open_questions_router, is_open_question
from code_ans import code_questions_router, is_code_test_question

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

    await state.set_state(QuizState.waiting_for_level)  # ⬅ Важно!
    logger.info(f"Пользователь {message.from_user.id} перешел к выбору уровня. Состояние: {await state.get_state()}")
    
    await message.answer(
        "🎯 <b>Выбери уровень сложности:</b>",
        reply_markup=get_level_keyboard(),
        parse_mode="HTML"
    )
    
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
    questions_queue = data.get("questions_queue", [])
    current_index = data.get("current_question_index", 0)
    
    if not current_level:
        await callback.answer("Сначала выбери уровень через /start", show_alert=True)
        return
    
    # Проверяем, есть ли ещё вопросы
    if current_index + 1 >= len(questions_queue):
        # ⬇ ВАЖНО: устанавливаем состояние ПЕРЕД очисткой!
        await state.set_state(QuizState.waiting_for_level)
        
        await callback.message.answer(
            f"🎉 <b>Поздравляем! Вы прошли все вопросы уровня {current_level}!</b>\n\n"
            f"Выбери новый уровень сложности:",
            reply_markup=get_level_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    # Берём следующий вопрос из очереди
    next_index = current_index + 1
    question_data = questions_queue[next_index]
    
    await state.update_data(
        current_question=question_data,
        current_question_index=next_index
    )
    
    if is_code_test_question(question_data):
        await state.set_state(QuizState.waiting_for_code)
        question_text = (
            f"💻 <b>Новое задание с тестами (Уровень {current_level}):</b>\n\n"
            f"{question_data['question']}\n\n"
            f"📝 <b>Шаблон кода:</b>\n<pre>{question_data.get('code_template', '')}</pre>\n\n"
            f"🧪 <b>Ваш код будет проверен на {len(question_data.get('tests', []))} тестах.</b>\n\n"
            f"<i>Отправьте ваш код сообщением:</i>"
        )
        await callback.message.answer(question_text, parse_mode="HTML")
    elif is_open_question(question_data):
        await state.set_state(QuizState.waiting_for_answer)
        await callback.message.answer(
            f"📝 <b>Новый вопрос (Уровень {current_level}):</b>\n{question_data['question']}\n\n💬 <i>Введите ваш ответ текстом:</i>",
            parse_mode="HTML"
        )
    else:
        await state.set_state(QuizState.waiting_for_answer)
        await callback.message.answer(
            f"📝 <b>Новый вопрос (Уровень {current_level}):</b>\n{question_data['question']}",
            reply_markup=get_question_inline_keyboard(question_data['options']),
            parse_mode="HTML"
        )
    
    await callback.answer()

@router.callback_query(F.data == "change_level")
async def change_level_handler(callback: CallbackQuery, state: FSMContext):
    # ⬇ НОВОЕ: Полностью очищаем состояние (включая очередь вопросов)
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
    
    await state.set_state(AddQuestionState.waiting_for_question_type)
    await message.answer(
        "📝 <b>Добавление нового вопроса</b>\n\n"
        "Шаг 1: Выберите тип вопроса:\n\n"
        "1️⃣ <b>С вариантами ответов</b> (пользователь выбирает из списка)\n"
        "2️⃣ <b>Открытый вопрос</b> (пользователь вводит ответ текстом)\n"
        "3️⃣ <b>Задание с кодом и тестами</b> (пользователь пишет код, бот проверяет на тестах)\n\n"
        "Введите 1, 2 или 3:",
        parse_mode="HTML"
    )

@router.message(AddQuestionState.waiting_for_question_type)
async def process_question_type(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    text = message.text.strip()
    
    if text == '1':
        await state.update_data(question_type='options')
        await state.set_state(AddQuestionState.waiting_for_question)
        await message.answer(
            "✅ Выбран тип: с вариантами ответов.\n\n"
            "Шаг 2/6: Введите текст вопроса:",
            parse_mode="HTML"
        )
    elif text == '2':
        await state.update_data(question_type='open')
        await state.set_state(AddQuestionState.waiting_for_question)
        await message.answer(
            "✅ Выбран тип: открытый вопрос.\n\n"
            "Шаг 2/5: Введите текст вопроса:",
            parse_mode="HTML"
        )
    elif text == '3':
        await state.update_data(question_type='code_test')
        await state.set_state(AddQuestionState.waiting_for_question)
        await message.answer(
            "✅ Выбран тип: задание с кодом и тестами.\n\n"
            "Шаг 2/6: Введите текст задания:",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Введите 1, 2 или 3.")

@router.message(AddQuestionState.waiting_for_question)
async def process_question_text(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    await state.update_data(question_text=message.text)
    data = await state.get_data()
    question_type = data.get('question_type')
    
    if question_type == 'options':
        await state.set_state(AddQuestionState.waiting_for_options)
        await message.answer(
            "✅ Текст вопроса сохранен.\n\n"
            "Шаг 3/6: Введите варианты ответов (каждый с новой строки).\n"
            "Минимум 2, максимум 10.",
            parse_mode="HTML"
        )
    elif question_type == 'open':
        await state.set_state(AddQuestionState.waiting_for_correct_answer)
        await message.answer(
            "✅ Текст вопроса сохранен.\n\n"
            "Шаг 3/5: Введите правильный ответ:",
            parse_mode="HTML"
        )
    elif question_type == 'code_test':
        await state.set_state(AddQuestionState.waiting_for_code_template)
        await message.answer(
            "✅ Текст задания сохранен.\n\n"
            "Шаг 3/6: Введите шаблон кода:\n\n"
            "<i>Пример:</i>\n<pre>n = int(input())\n# Ваш код здесь\n</pre>",
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
    
    # Показываем пронумерованные варианты
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
    await message.answer(
        "✅ Варианты сохранены.\n\n"
        f"<b>Ваши варианты:</b>\n{options_text}\n\n"
        "Шаг 4/6: Введите номер правильного ответа (1, 2, 3...):",
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
            "Шаг 5/6: Введите объяснение правильного ответа "
            "(почему этот ответ верный):",
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer("❌ Введите число. Попробуйте снова:")

@router.message(AddQuestionState.waiting_for_correct_answer)
async def process_correct_answer(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    await state.update_data(correct_answer=message.text.strip())
    await state.set_state(AddQuestionState.waiting_for_explanation)
    await message.answer(
        "✅ Правильный ответ сохранен.\n\n"
        "Шаг 4/5: Введите объяснение правильного ответа "
        "(почему этот ответ верный):",
        parse_mode="HTML"
    )



@router.message(AddQuestionState.waiting_for_code_template)
async def process_code_template(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    await state.update_data(code_template=message.text)
    await state.set_state(AddQuestionState.waiting_for_tests)
    await message.answer(
        "✅ Шаблон сохранен.\n\n"
        "Шаг 4/6: Введите тесты в следующем формате:\n\n"
        "<pre>INPUT:\n4\nOUTPUT:\n1 1 1 5\n1 1 1 5\n1 1 1 5\n1 1 1 5\n===\nINPUT:\n3\nOUTPUT:\n1 1 5\n1 1 5\n1 1 5</pre>\n\n"
        "Разделяйте тесты строкой <code>===</code>.\n"
        "Можно добавить столько тестов, сколько нужно.",
        parse_mode="HTML"
    )

@router.message(AddQuestionState.waiting_for_tests)
async def process_tests(message: Message, state: FSMContext):
    """Обработка ввода тестов для задания с кодом"""
    if not is_admin(message):
        return
    
    # Парсим тесты из текста
    raw = message.text.strip()
    test_blocks = [b.strip() for b in raw.split('===') if b.strip()]
    
    tests = []
    for i, block in enumerate(test_blocks, 1):
        lines = block.split('\n')
        input_lines = []
        output_lines = []
        current_section = None
        
        for line in lines:
            stripped = line.strip().upper()
            if stripped.startswith('INPUT'):
                current_section = 'input'
                # Если после INPUT: есть что-то на той же строке
                after_colon = line.split(':', 1)[1].strip() if ':' in line else ''
                if after_colon:
                    input_lines.append(after_colon)
            elif stripped.startswith('OUTPUT'):
                current_section = 'output'
                after_colon = line.split(':', 1)[1].strip() if ':' in line else ''
                if after_colon:
                    output_lines.append(after_colon)
            elif current_section == 'input':
                input_lines.append(line)
            elif current_section == 'output':
                output_lines.append(line)
        
        if not input_lines and not output_lines:
            await message.answer(
                f"❌ Не удалось распарсить тест #{i}. Проверьте формат.\n\n"
                "Правильный формат:\n"
                "<pre>INPUT:\n4\nOUTPUT:\n1 1 1 5\n===\nINPUT:\n3\nOUTPUT:\n1 1 5</pre>",
                parse_mode="HTML"
            )
            return
        
        tests.append({
            "input": '\n'.join(input_lines).strip(),
            "output": '\n'.join(output_lines).strip()
        })
    
    if len(tests) < 1:
        await message.answer("❌ Не найдено ни одного теста. Проверьте формат.")
        return
    
    await state.update_data(tests=tests)
    await state.set_state(AddQuestionState.waiting_for_explanation)
    
    # Показываем превью тестов
    preview = "\n\n".join([
        f"Тест #{i+1}:\n  input: {t['input'][:50]}\n  output: {t['output'][:50]}"
        for i, t in enumerate(tests)
    ])
    
    await message.answer(
        f"✅ Сохранено тестов: {len(tests)}\n\n{preview}\n\n"
        "Шаг 5/6: Введите объяснение / подсказку к заданию:",
        parse_mode="HTML"
    )

@router.callback_query(QuizState.waiting_for_level, F.data.startswith("level_"))
async def process_level_selection(callback: CallbackQuery, state: FSMContext):
    try:
        logger.info(f"Получен callback: {callback.data}")
        
        level = int(callback.data.split("_")[1]) 
        logger.info(f"Пользователь {callback.from_user.id} выбрал уровень {level}.")
        
        await state.update_data(current_level=level)
        available_questions = get_questions_by_level(level)
        
        if not available_questions:
            await callback.message.edit_text(
                f"😔 К сожалению, вопросов для уровня {level} пока нет.",
                reply_markup=None
            )
            await state.clear()
            await callback.answer()
            return
        
        # ⬇ НОВОЕ: Перемешиваем вопросы и сохраняем в состояние
        shuffled_questions = available_questions.copy()
        random.shuffle(shuffled_questions)
        
        await state.update_data(
            questions_queue=shuffled_questions,
            current_question_index=0
        )
        
        # Берём первый вопрос из перемешанного списка
        question_data = shuffled_questions[0]
        await state.update_data(current_question=question_data)
        
        # Определяем тип вопроса
        if is_code_test_question(question_data):
            await state.set_state(QuizState.waiting_for_code)
            question_text = (
                f"💻 <b>Задание с тестами (Уровень {level}):</b>\n\n"
                f"{question_data['question']}\n\n"
                f"📝 <b>Шаблон кода:</b>\n<pre>{question_data.get('code_template', '')}</pre>\n\n"
                f"🧪 <b>Ваш код будет проверен на {len(question_data.get('tests', []))} тестах.</b>\n\n"
                f"<i>Отправьте ваш код сообщением:</i>"
            )
            await callback.message.edit_text(question_text, reply_markup=None, parse_mode="HTML")
        elif is_open_question(question_data):
            await state.set_state(QuizState.waiting_for_answer)
            await callback.message.edit_text(
                f" <b>Вопрос (Уровень {level}):</b>\n{question_data['question']}\n\n💬 <i>Введите ваш ответ текстом:</i>",
                reply_markup=None,
                parse_mode="HTML"
            )
        else:
            await state.set_state(QuizState.waiting_for_answer)
            await callback.message.edit_text(
                f"📝 <b>Вопрос (Уровень {level}):</b>\n{question_data['question']}",
                reply_markup=get_question_inline_keyboard(question_data['options']),
                parse_mode="HTML"
            )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка в process_level_selection: {e}", exc_info=True)
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
        
@router.message(AddQuestionState.waiting_for_explanation)
async def process_explanation(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    
    await state.update_data(explanation=message.text)
    await state.set_state(AddQuestionState.waiting_for_level)
    
    data = await state.get_data()
    question_type = data.get('question_type')
    
    # Нумерация шагов для разных типов
    steps = {
        'options': '6/6',
        'open': '5/5',
        'code_test': '6/6'
    }
    step_text = f"Шаг {steps.get(question_type, '6/6')}: Выберите уровень сложности:\n"
    
    await message.answer(
        "✅ Объяснение сохранено.\n\n"
        f"{step_text}"
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
            await message.answer("❌ Уровень должен быть 1, 2 или 3.")
            return
    except ValueError:
        await message.answer("❌ Введите число.")
        return
    
    data = await state.get_data()
    question_type = data.get('question_type')
    
    if question_type == 'open':
        new_question = {
            "question": data.get('question_text'),
            "correct_answer": data.get('correct_answer'),
            "explanation": data.get('explanation'),
            "level": level
        }
        question_info = f"<b>Ответ:</b> {new_question['correct_answer']}"
    elif question_type == 'code_test':
        new_question = {
            "question": data.get('question_text'),
            "code_template": data.get('code_template'),
            "tests": data.get('tests', []),
            "explanation": data.get('explanation'),
            "level": level,
            "type": "code_test"
        }
        question_info = f"<b>Тестов:</b> {len(new_question['tests'])}"
    else:  # options
        new_question = {
            "question": data.get('question_text'),
            "options": data.get('options'),
            "correct_index": data.get('correct_index'),
            "explanation": data.get('explanation'),
            "level": level
        }
        question_info = f"<b>Вариантов:</b> {len(new_question['options'])}"
    
    Questions_db.append(new_question)
    
    if save_questions(Questions_db):
        type_names = {
            'options': 'с вариантами',
            'open': 'открытый',
            'code_test': 'с кодом и тестами'
        }
        await message.answer(
            f"✅ <b>Вопрос ({type_names[question_type]}) добавлен!</b>\n\n"
            f"<b>Вопрос:</b> {new_question['question']}\n"
            f"<b>Уровень:</b> {level}\n"
            f"{question_info}",
            parse_mode="HTML",
            reply_markup=replyKeyboard()
        )
    
    await state.clear()

@router.message(Command('view_questions'))
async def view_questions(message: Message):
    """Показывает статистику по вопросам (только для админа)"""
    if not is_admin(message):
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if not Questions_db:
        await message.answer("📭 База вопросов пуста.")
        return
    
    stats = {}
    for q in Questions_db:
        level = q.get('level', 0)
        stats[level] = stats.get(level, 0) + 1
    
    response = "📊 <b>Статистика вопросов:</b>\n\n"
    response += f"Всего вопросов: {len(Questions_db)}\n\n"
    
    for level in sorted(stats.keys()):
        level_name = {1: "Легкий", 2: "Средний", 3: "Сложный"}.get(level, f"Уровень {level}")
        response += f"• {level_name} (Уровень {level}): {stats[level]} вопросов\n"
    
    await message.answer(response, parse_mode="HTML")

@router.message(F.text == '⚙️ Админ панель')
async def admin_panel(message: Message):
    """Админ панель через кнопку"""
    if not is_admin(message):
        await message.answer("❌ У вас нет доступа к админ панели.")
        return
    
    await message.answer(
        "⚙️ <b>Админ панель</b>\n\n"
        "Доступные команды:\n"
        "/add_question - Добавить новый вопрос\n"
        "/view_questions - Посмотреть статистику вопросов",
        parse_mode="HTML"
    )

router.include_router(open_questions_router)
router.include_router(code_questions_router)