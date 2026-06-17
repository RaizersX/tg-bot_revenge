from aiogram.fsm.state import State, StatesGroup

class QuizState(StatesGroup):
    waiting_for_answer = State()