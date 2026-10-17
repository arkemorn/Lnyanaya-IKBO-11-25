"""Консольная оболочка и виртуальная файловая система в памяти."""

import copy
import posixpath
import platform
import shlex
import zipfile
from pathlib import Path, PurePosixPath

ROOT_PATH = "/"
CURRENT_PATH = "."
DEFAULT_VFS_NAME = "memory"
DIRECTORY = "dir"
FILE = "file"
EMPTY_COUNT = 0
ONE_ARGUMENT = 1
TWO_ARGUMENTS = 2
THREE_ARGUMENTS = 3
DEFAULT_HEAD_LINES = 10
ROOT_PARTS = {"/", "//", "", "."}
INVALID_ARCHIVE_PARTS = {".", ".."}


class ShellError(Exception):
    """Ошибка выполнения команды или загрузки виртуальной системы."""


class Node:
    """Представляет файл или каталог виртуальной файловой системы."""

    def __init__(self, name, kind=DIRECTORY, data=b""):
        """Создаёт узел с именем, типом и содержимым."""
        self.name = name
        self.kind = kind
        self.data = data
        self.children = {}


class VirtualFileSystem:
    """Хранит дерево файлов и каталогов только в оперативной памяти."""

    def __init__(self, name=DEFAULT_VFS_NAME):
        """Создаёт пустую файловую систему с указанным именем."""
        self.name = name
        self.root = Node(ROOT_PATH)
        self.cwd = ROOT_PATH

    def load_zip(self, archive_path):
        """Загружает содержимое ZIP-архива в память без распаковки."""
        root = Node(ROOT_PATH)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                for entry in archive.infolist():
                    self._insert_archive_entry(root, archive, entry)
        except zipfile.BadZipFile as exc:
            raise ShellError("неверный формат ZIP-архива") from exc

        self.root = root
        self.cwd = ROOT_PATH
        self.name = Path(archive_path).stem or DEFAULT_VFS_NAME

    @staticmethod
    def _archive_parts(entry_name):
        """Проверяет путь из ZIP-архива и возвращает его компоненты."""
        if "\\" in entry_name:
            raise ShellError(f"неверный путь в архиве: {entry_name}")

        path = PurePosixPath(entry_name)
        parts = path.parts
        if path.is_absolute() or any(
            part in INVALID_ARCHIVE_PARTS for part in parts
        ):
            raise ShellError(f"неверный путь в архиве: {entry_name}")

        return tuple(part for part in parts if part not in ROOT_PARTS)

    @staticmethod
    def _ensure_directory(root, parts):
        """Находит или создаёт каталог по последовательности компонентов."""
        current = root
        for part in parts:
            child = current.children.get(part)
            if child is None:
                child = Node(part)
                current.children[part] = child
            elif child.kind != DIRECTORY:
                raise ShellError(f"путь проходит через файл: {part}")
            current = child
        return current

    def _insert_archive_entry(self, root, archive, entry):
        """Добавляет один файл или каталог из архива в дерево."""
        parts = self._archive_parts(entry.filename)
        if not parts:
            return

        parent = self._ensure_directory(root, parts[:-1])
        name = parts[-1]
        existing = parent.children.get(name)

        if entry.is_dir():
            if existing is not None and existing.kind != DIRECTORY:
                raise ShellError(f"конфликт типов в архиве: {entry.filename}")
            parent.children.setdefault(name, Node(name))
            return

        if existing is not None:
            raise ShellError(f"повторяющийся путь в архиве: {entry.filename}")
        parent.children[name] = Node(name, FILE, archive.read(entry))

    @staticmethod
    def _path_parts(path, cwd):
        """Нормализует путь и возвращает его компоненты."""
        target = path if path.startswith(ROOT_PATH) else posixpath.join(
            cwd, path
        )
        normalized = posixpath.normpath(target)
        return tuple(
            part for part in PurePosixPath(normalized).parts
            if part not in ROOT_PARTS
        )

    def resolve(self, path=CURRENT_PATH):
        """Находит файл или каталог по абсолютному либо относительному пути."""
        node = self.root
        for part in self._path_parts(path, self.cwd):
            if node.kind != DIRECTORY or part not in node.children:
                raise ShellError(f"нет такого файла или каталога: {path}")
            node = node.children[part]
        return node

    def list_dir(self, path=CURRENT_PATH):
        """Возвращает отсортированное содержимое каталога."""
        node = self.resolve(path)
        if node.kind != DIRECTORY:
            return node.name
        return "\n".join(sorted(node.children)) or "(пусто)"

    def change_dir(self, path=ROOT_PATH):
        """Меняет текущий каталог и возвращает его виртуальный путь."""
        node = self.resolve(path)
        if node.kind != DIRECTORY:
            raise ShellError(f"не каталог: {path}")
        parts = self._path_parts(path, self.cwd)
        self.cwd = ROOT_PATH + "/".join(parts) if parts else ROOT_PATH
        return self.cwd

    def read_lines(self, path):
        """Читает текстовый файл и разбивает его на строки."""
        node = self.resolve(path)
        if node.kind != FILE:
            raise ShellError(f"не файл: {path}")
        try:
            return node.data.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise ShellError(f"файл не является текстовым: {path}") from exc

    def copy(self, source, destination):
        """Копирует файл или каталог внутри виртуальной системы."""
        source_node = self.resolve(source)
        if source_node is self.root:
            raise ShellError("нельзя скопировать корневой каталог")
        parent, name = self._copy_target(source_node, destination)
        if name in parent.children:
            raise ShellError(f"назначение уже существует: {destination}")

        cloned = copy.deepcopy(source_node)
        cloned.name = name
        parent.children[name] = cloned

    def _copy_target(self, source_node, destination):
        """Определяет каталог и имя назначения для команды cp."""
        try:
            existing = self.resolve(destination)
        except ShellError:
            existing = None
        if existing is not None and existing.kind == DIRECTORY:
            return existing, source_node.name

        parts = self._path_parts(destination, self.cwd)
        if not parts:
            return self.root, source_node.name
        parent_path = ROOT_PATH + "/".join(parts[:-1])
        parent = self.resolve(parent_path)
        if parent.kind != DIRECTORY:
            raise ShellError("родительский путь не является каталогом")
        return parent, parts[-1]


class Shell:
    """Разбирает команды и выполняет их над виртуальной файловой системой."""

    def __init__(self, vfs):
        """Создаёт оболочку для указанной виртуальной файловой системы."""
        self.vfs = vfs
        self._commands = {
            "ls": self._command_ls,
            "cd": self._command_cd,
            "head": self._command_head,
            "uniq": self._command_uniq,
            "uname": self._command_uname,
            "cp": self._command_cp,
            "exit": self._command_exit,
        }

    @property
    def prompt(self):
        """Возвращает приглашение с именем VFS и текущим каталогом."""
        shown_path = "~" if self.vfs.cwd == ROOT_PATH else "~" + self.vfs.cwd
        return f"user@{self.vfs.name}:{shown_path}$"

    def execute(self, line):
        """Выполняет введённую строку и возвращает ответ и признак выхода."""
        try:
            arguments = shlex.split(line, comments=True, posix=True)
        except ValueError as exc:
            return f"ошибка синтаксиса: {exc}", False

        if not arguments:
            return "", False

        command, *values = arguments
        handler = self._commands.get(command)
        if handler is None:
            return f"ошибка: команда не найдена: {command}", False

        try:
            return handler(values)
        except ShellError as exc:
            return f"ошибка: {exc}", False

    def _command_ls(self, arguments):
        """Выводит содержимое текущего или указанного каталога."""
        if len(arguments) > ONE_ARGUMENT:
            raise ShellError("использование: ls [путь]")
        path = arguments[0] if arguments else CURRENT_PATH
        return self.vfs.list_dir(path), False

    def _command_cd(self, arguments):
        """Меняет текущий каталог виртуальной файловой системы."""
        if len(arguments) > ONE_ARGUMENT:
            raise ShellError("использование: cd [путь]")
        path = arguments[0] if arguments else ROOT_PATH
        return self.vfs.change_dir(path), False

    def _command_head(self, arguments):
        """Показывает заданное число первых строк текстового файла."""
        if len(arguments) == ONE_ARGUMENT:
            count = DEFAULT_HEAD_LINES
            filename = arguments[0]
        elif (
            len(arguments) == THREE_ARGUMENTS
            and arguments[0] == "-n"
            and arguments[1].isdigit()
        ):
            count = int(arguments[1])
            filename = arguments[2]
        else:
            raise ShellError("использование: head [-n число] файл")

        if count < EMPTY_COUNT:
            raise ShellError("число строк не может быть отрицательным")
        return "\n".join(self.vfs.read_lines(filename)[:count]), False

    def _command_uniq(self, arguments):
        """Удаляет соседние повторяющиеся строки из текстового файла."""
        if len(arguments) != ONE_ARGUMENT:
            raise ShellError("использование: uniq файл")
        lines = self.vfs.read_lines(arguments[0])
        unique_lines = []
        for line in lines:
            if not unique_lines or unique_lines[-1] != line:
                unique_lines.append(line)
        return "\n".join(unique_lines), False

    def _command_uname(self, arguments):
        """Выводит имя операционной системы хоста."""
        if arguments:
            raise ShellError("использование: uname")
        return platform.system(), False

    def _command_cp(self, arguments):
        """Копирует файл или каталог в виртуальной файловой системе."""
        if len(arguments) != TWO_ARGUMENTS:
            raise ShellError("использование: cp источник назначение")
        self.vfs.copy(arguments[0], arguments[1])
        return "", False

    @staticmethod
    def _command_exit(arguments):
        """Завершает оболочку, если команда не получила аргументов."""
        if arguments:
            raise ShellError("exit не принимает аргументы")
        return "Выход из эмулятора", True
