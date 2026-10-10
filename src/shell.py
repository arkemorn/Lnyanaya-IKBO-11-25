
"""Простой командный интерпретатор для первого этапа."""
import shlex


class ShellError(Exception):
    """Ошибка выполнения команды."""


class Shell:
    def __init__(self):
        self.cwd = "/"

    def execute(self, line):
        """Возвращает текст ответа и признак завершения приложения."""
        try:
            args = shlex.split(line)
        except ValueError as exc:
            return f"Ошибка синтаксиса: {exc}", False

        if not args:
            return "", False

        command, *values = args

        if command == "exit":
            if values:
                return "Ошибка: exit не принимает аргументы", False
            return "Выход из эмулятора", True

        if command == "ls":
            if len(values) > 1:
                return "Использование: ls [путь]", False
            return "Заглушка ls: виртуальная файловая система появится на следующем этапе", False

        if command == "cd":
            if len(values) > 1:
                return "Использование: cd [путь]", False
            return "Заглушка cd: виртуальная файловая система появится на следующем этапе", False

        return f"Ошибка: команда не найдена: {command}", False
