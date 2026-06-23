from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from quest import QuizState
import random
import logging

logger = logging.getLogger(__name__)

open_questions_router = Router()


def is_open_question(question: dict) -> bool:
    """Проверить, является ли вопрос открытым (без вариантов ответа)"""
    return "options" not in question or not question.get("options")


def normalize_answer(answer: str) -> str:
    """Нормализовать ответ для сравнения"""
    return answer.strip().lower()


def check_answer(user_answer: str, correct_answer: str) -> bool:
    """Проверить правильность ответа с учетом возможных вариаций"""
    user_normalized = normalize_answer(user_answer)
    correct_normalized = normalize_answer(correct_answer)
    
    # Точное совпадение
    if user_normalized == correct_normalized:
        return True
    
    # Если ответ содержит ключевые слова из правильного ответа
    correct_words = set(correct_normalized.split())
    user_words = set(user_normalized.split())
    
    # Если пользователь написал хотя бы 70% ключевых слов
    if correct_words and len(correct_words & user_words) / len(correct_words) >= 0.7:
        return True
    
    return False


@open_questions_router.message(QuizState.waiting_for_answer, F.text & ~F.text.startswith('/'))
async def process_open_answer(message: Message, state: FSMContext):
    """Обработка текстового ответа на открытый вопрос"""
    data = await state.get_data()
    current_question = data.get('current_question')
    
    if not current_question:
        return
    
    # Проверяем, что это открытый вопрос
    if not is_open_question(current_question):
        return
    
    user_answer = message.text.strip()
    correct_answer = current_question.get('correct_answer', '')
    
    # Проверяем правильность ответа
    if check_answer(user_answer, correct_answer):
        result_text = "✅ Правильно! Молодец!"
    else:
        explanation = current_question.get('explanation', 'Объяснение отсутствует.')
        result_text = f"❌ Неверно.\n\n<b>Правильный ответ:</b> {correct_answer}\n\n<b>Почему:</b> {explanation}"
    
    await message.answer(
        result_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="next_question")],
            [InlineKeyboardButton(text="🔄 Сменить уровень", callback_data="change_level")]
        ])
    )
    
    # Очищаем состояние, но сохраняем уровень
    current_level = data.get('current_level')
    await state.clear()
    if current_level:
        await state.update_data(current_level=current_level)