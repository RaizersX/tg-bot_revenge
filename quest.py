from aiogram.fsm.state import State, StatesGroup

class QuizState(StatesGroup):
    waiting_for_level = State()
    waiting_for_answer = State()

class AddQuestionState(StatesGroup):
    waiting_for_question = State()
    waiting_for_options = State()
    waiting_for_correct_index = State()
    waiting_for_explanation = State()
    waiting_for_level = State()