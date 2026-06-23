from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from quest import QuizState
from code_executor import run_tests
import logging
import html 

logger = logging.getLogger(__name__)

code_questions_router = Router()


def is_code_test_question(question: dict) -> bool:
    """Вопрос с кодом и тестами"""
    return question.get("type") == "code_test"


def escape(text: str) -> str:
    """Экранирует HTML-символы в тексте"""
    if not text:
        return ""
    return html.escape(text)


def format_tests_result(test_results: dict) -> str:
    """Форматирует результаты тестов в красивое сообщение"""
    passed = test_results['passed']
    total = test_results['total']
    
    if passed == total:
        header = f"✅ <b>Отлично! Пройдено тестов: {passed}/{total}</b>\n\n"
    else:
        header = f"❌ <b>Пройдено тестов: {passed}/{total}</b>\n\n"
    
    details = []
    for res in test_results['results']:
        num = res['test_num']
        if res['passed']:
            details.append(f"  ✅ Тест #{num}: пройден")
        else:
            if res['error']:
                # ⬇ ЭКРАНИРУЕМ stderr
                error_text = escape(res['error'])[:200]
                details.append(f"  ❌ Тест #{num}: ошибка выполнения\n     <pre>{error_text}</pre>")
            else:
                details.append(f"  ❌ Тест #{num}: неверный ответ")
                # ⬇ ЭКРАНИРУЕМ expected и actual
                expected_text = escape(res['expected'])[:200]
                actual_text = escape(res['actual'])[:200]
                details.append(f"     <b>Ожидалось:</b>\n<pre>{expected_text}</pre>")
                details.append(f"     <b>Получено:</b>\n<pre>{actual_text}</pre>")
    
    return header + "\n".join(details)

@code_questions_router.message(QuizState.waiting_for_code, F.text & ~F.text.startswith('/'))
async def process_code_answer(message: Message, state: FSMContext):
    """Обработка кода от пользователя"""
    data = await state.get_data()
    current_question = data.get('current_question')
    
    if not current_question or not is_code_test_question(current_question):
        return
    
    user_code = message.text
    code_template = current_question.get('code_template', '')
    
    if '# Ваш код здесь' in code_template:
        full_code = code_template.replace('# Ваш код здесь', user_code)
    else:
        full_code = code_template + '\n' + user_code
    
    tests = current_question.get('tests', [])
    
    if not tests:
        await message.answer("❌ Ошибка: у задания нет тестов.")
        return
    
    await message.answer("⏳ Выполняю ваш код на тестах...")
    test_results = run_tests(full_code, tests)
    
    result_text = format_tests_result(test_results)
    
    if test_results['passed'] == test_results['total']:
        result_text += "\n\n🎉 <b>Задание решено верно!</b>"
    else:
        explanation = current_question.get('explanation', '')
        if explanation:
            result_text += f"\n\n💡 <b>Подсказка:</b>\n{html.escape(explanation)}"
    
    # ⬇ СОХРАНЯЕМ важные данные перед очисткой
    current_level = data.get('current_level')
    questions_queue = data.get('questions_queue', [])
    current_question_index = data.get('current_question_index', 0)
    
    await state.clear()
    
    # ⬇ ВОССТАНАВЛИВАЕМ данные
    await state.update_data(
        current_level=current_level,
        questions_queue=questions_queue,
        current_question_index=current_question_index
    )
    
    await message.answer(
        result_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➡️ Следующий вопрос", callback_data="next_question")],
            [InlineKeyboardButton(text="🔄 Сменить уровень", callback_data="change_level")]
        ])
    )