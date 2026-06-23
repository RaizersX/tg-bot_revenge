import subprocess
import tempfile
import os
import logging
from typing import Tuple, List, Dict

logger = logging.getLogger(__name__)


def execute_code(code: str, timeout: int = 5) -> Tuple[bool, str, str]:
    """Безопасно выполняет Python-код без входных данных"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()
        )
        
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    
    except subprocess.TimeoutExpired:
        return False, "", f"⏱ Время выполнения превышено (лимит {timeout}с)"
    except Exception as e:
        return False, "", f"Ошибка выполнения: {str(e)}"
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass


def execute_code_with_input(code: str, input_data: str, timeout: int = 5) -> Tuple[bool, str, str]:
    """
    Выполняет Python-код с передачей входных данных через stdin
    
    Args:
        code: Python-код
        input_data: данные для input()
        timeout: максимальное время выполнения
    
    Returns:
        (success, stdout, stderr)
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ['python', temp_file],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=tempfile.gettempdir()
        )
        
        return result.returncode == 0, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        return False, "", f"⏱ Время выполнения превышено (лимит {timeout}с)"
    except Exception as e:
        return False, "", f"Ошибка выполнения: {str(e)}"
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass


def normalize_output(output: str) -> str:
    """
    Нормализует вывод программы для сравнения:
    - убирает пробелы в конце каждой строки
    - убирает пустые строки в конце
    - приводит \r\n к \n
    """
    if not output:
        return ""
    
    lines = output.replace('\r\n', '\n').split('\n')
    # Убираем пробелы в конце каждой строки
    lines = [line.rstrip() for line in lines]
    # Убираем пустые строки в конце
    while lines and lines[-1] == '':
        lines.pop()
    return '\n'.join(lines)


def run_tests(code: str, tests: List[Dict], timeout: int = 5) -> Dict:
    """
    Запускает код на всех тестах и возвращает результаты
    
    Args:
        code: код пользователя
        tests: список тестов [{"input": "...", "output": "..."}, ...]
        timeout: таймаут на один тест
    
    Returns:
        {
            "passed": количество пройденных тестов,
            "total": всего тестов,
            "results": [{"test_num": 1, "passed": True/False, "actual": "...", "expected": "...", "error": "..."}]
        }
    """
    results = []
    passed_count = 0
    
    for i, test in enumerate(tests, 1):
        input_data = test.get('input', '')
        expected_output = test.get('output', '')
        
        success, stdout, stderr = execute_code_with_input(code, input_data, timeout)
        
        if not success:
            results.append({
                "test_num": i,
                "passed": False,
                "actual": "",
                "expected": expected_output,
                "error": stderr
            })
        else:
            normalized_actual = normalize_output(stdout)
            normalized_expected = normalize_output(expected_output)
            is_passed = normalized_actual == normalized_expected
            
            if is_passed:
                passed_count += 1
            
            results.append({
                "test_num": i,
                "passed": is_passed,
                "actual": stdout.strip(),
                "expected": expected_output,
                "error": ""
            })
    
    return {
        "passed": passed_count,
        "total": len(tests),
        "results": results
    }


def check_code_output(user_output: str, expected_output: str) -> bool:
    """Сравнивает вывод пользователя с ожидаемым (для простых заданий без тестов)"""
    user_normalized = normalize_output(user_output)
    expected_normalized = normalize_output(expected_output)
    
    if user_normalized == expected_normalized:
        return True
    
    if '|' in expected_output:
        variants = [normalize_output(v) for v in expected_output.split('|')]
        return user_normalized in variants
    
    return False