"""Командный интерпретатор и виртуальная файловая система."""
import base64
import csv
import os
import shlex
import socket
from pathlib import PurePosixPath


class ShellError(Exception):
    """Ошибка команды или виртуальной файловой системы."""


class Node:
    """Один файл или каталог в виртуальной файловой системе."""
    def __init__(self, name, kind="dir", data=""):
        self.name = name
        self.kind = kind
        self.data = data
        self.children = {}


class VirtualFileSystem:
    """Хранит файлы и каталоги только в оперативной памяти."""
    def __init__(self):
        self.root = Node("/")
        self.cwd = "/"

    def load_csv(self, filename):
        """Загрузить CSV со столбцами path,type,content_base64."""
        root = Node("/")
        with open(filename, newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            required = {"path", "type", "content_base64"}
            if not reader.fieldnames or not required.issubset(reader.fieldnames):
                raise ShellError("неверный формат CSV: нужны path,type,content_base64")
            rows = list(reader)
        for row in rows:
            path = row["path"].strip("/")
            if not path:
                continue
            parts = PurePosixPath(path).parts
            current = root
            for part in parts[:-1]:
                if part not in current.children:
                    current.children[part] = Node(part)
                parent = current.children[part]
                if parent.kind != "dir":
                    raise ShellError(f"путь проходит через файл: {part}")
                current = parent
            name = parts[-1]
            kind = row["type"].strip()
            if kind not in {"dir", "file"}:
                raise ShellError(f"неизвестный тип элемента: {kind}")
            data = ""
            if kind == "file" and row["content_base64"]:
                try:
                    data = base64.b64decode(
                        row["content_base64"], validate=True
                    ).decode("utf-8")
                except (ValueError, UnicodeDecodeError) as exc:
                    raise ShellError(f"неверные данные файла {path}") from exc
            if name in current.children and current.children[name].kind != kind:
                raise ShellError(f"конфликт типов для {path}")
            current.children[name] = Node(name, kind, data)
        self.root = root
        self.cwd = "/"

    def parts(self, path):
        import posixpath
        target = path if path.startswith("/") else f"{self.cwd}/{path}"
        target = posixpath.normpath("/" + target.lstrip("/"))
        result = []
        for part in PurePosixPath(target).parts:
            if part in {"/", "//", "", "."}:
                continue
            if part == "..":
                if result:
                    result.pop()
            else:
                result.append(part)
        return result

    def resolve(self, path=".", allow_missing=False):
        node = self.root
        for part in self.parts(path):
            if node.kind != "dir" or part not in node.children:
                if allow_missing:
                    return None
                raise ShellError(f"нет такого файла или каталога: {path}")
            node = node.children[part]
        return node

    def parent_and_name(self, path):
        parts = self.parts(path)
        if not parts:
            raise ShellError("нельзя изменить корневой каталог")
        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1])
        parent = self.resolve(parent_path)
        if parent.kind != "dir":
            raise ShellError("родительский путь не является каталогом")
        return parent, name

    def list_dir(self, path="."):
        node = self.resolve(path)
        if node.kind != "dir":
            return node.name
        return "\n".join(sorted(node.children)) or "(пусто)"

    def change_dir(self, path="."):
        node = self.resolve(path)
        if node.kind != "dir":
            raise ShellError(f"не каталог: {path}")
        parts = self.parts(path)
        self.cwd = "/" + "/".join(parts) if parts else "/"
        return self.cwd

    def disk_usage(self, node=None):
        node = node or self.root
        if node.kind == "file":
            return len(node.data.encode("utf-8"))
        return sum(self.disk_usage(child) for child in node.children.values())

    def copy(self, source, destination):
        import copy
        src = self.resolve(source)
        parent, name = self.parent_and_name(destination)
        if name in parent.children:
            raise ShellError(f"назначение уже существует: {destination}")
        cloned = copy.deepcopy(src)
        cloned.name = name
        parent.children[name] = cloned

    def move(self, source, destination):
        src_parent, src_name = self.parent_and_name(source)
        if src_name not in src_parent.children:
            raise ShellError(f"нет такого файла или каталога: {source}")
        dst_parent, dst_name = self.parent_and_name(destination)
        if dst_name in dst_parent.children:
            raise ShellError(f"назначение уже существует: {destination}")
        node = src_parent.children[src_name]
        if node.kind == "dir" and destination in {source, source + "/."}:
            raise ShellError("нельзя переместить каталог в самого себя")
        dst_parent.children[dst_name] = src_parent.children.pop(src_name)
        dst_parent.children[dst_name].name = dst_name


class Shell:
    """Выполняет команды над виртуальной файловой системой."""
    def __init__(self, vfs=None, vfs_path=None, script_path=None, prompt=None):
        self.vfs = vfs or VirtualFileSystem()
        self.vfs_path = vfs_path or "(память)"
        self.script_path = script_path or "(не задан)"
        self.prompt = prompt or "user@vfs:~$"

    def conf_dump(self):
        return "\n".join([
            f"vfs_path={self.vfs_path}",
            f"script_path={self.script_path}",
            f"prompt={self.prompt}",
        ])

    def execute(self, line):
        """Вернуть (текст ответа, нужно ли закрыть приложение)."""
        try:
            args = shlex.split(line, comments=False, posix=True)
        except ValueError as exc:
            return f"ошибка синтаксиса: {exc}", False
        if not args:
            return "", False
        command, *values = args
        try:
            if command == "exit":
                if values:
                    raise ShellError("exit: лишние аргументы")
                return "logout", True
            if command == "conf-dump":
                if values:
                    raise ShellError("использование: conf-dump")
                return self.conf_dump(), False
            if command == "ls":
                path = values[-1] if values else "."
                return self.vfs.list_dir(path), False
            if command == "cd":
                if len(values) > 1:
                    raise ShellError("использование: cd [путь]")
                return self.vfs.change_dir(values[0] if values else "/"), False
            if command == "tail":
                count = 10
                if len(values) == 1:
                    filename = values[0]
                elif len(values) == 3 and values[0] == "-n" and values[1].isdigit():
                    count = int(values[1])
                    filename = values[2]
                else:
                    raise ShellError("использование: tail [-n число] файл")
                node = self.vfs.resolve(filename)
                if node.kind != "file":
                    raise ShellError(f"не файл: {filename}")
                lines = node.data.splitlines()
                return "\n".join(lines[-count:]), False
            if command == "uname":
                if values:
                    raise ShellError("использование: uname")
                return f"VFS-Shell {socket.gethostname()}", False
            if command == "du":
                path = values[0] if values else "."
                if len(values) > 1:
                    raise ShellError("использование: du [путь]")
                node = self.vfs.resolve(path)
                return f"{self.vfs.disk_usage(node)}\t{path}", False
            if command in {"cp", "mv"}:
                if len(values) != 2:
                    raise ShellError(f"использование: {command} источник назначение")
                if command == "cp":
                    self.vfs.copy(values[0], values[1])
                else:
                    self.vfs.move(values[0], values[1])
                return "", False
            raise ShellError(f"команда не найдена: {command}")
        except ShellError as exc:
            return f"ошибка: {exc}", False
