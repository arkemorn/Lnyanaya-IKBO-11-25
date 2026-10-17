"""Модульные тесты виртуальной файловой системы и команд."""

import pathlib
import platform
import tempfile
import unittest
import zipfile

from src.shell import Node, Shell, ShellError, VirtualFileSystem


class ShellTests(unittest.TestCase):
    """Проверяет команды оболочки на временной виртуальной системе."""

    def __init__(self, method_name="runTest"):
        """Создаёт отдельную VFS для каждого тестового метода."""
        super().__init__(method_name)
        self.set_up()

    def set_up(self):
        """Подготавливает файлы и оболочку для текущего теста."""
        self.vfs = VirtualFileSystem("test-vfs")
        self.vfs.root.children["notes.txt"] = Node(
            "notes.txt", "file", b"first\nsecond\nthird\n"
        )
        self.vfs.root.children["duplicates.txt"] = Node(
            "duplicates.txt", "file", b"one\none\ntwo\ntwo\nthree\n"
        )
        self.vfs.root.children["notes with spaces.txt"] = Node(
            "notes with spaces.txt",
            "file",
            b"first spaced line\nsecond spaced line\n",
        )
        self.vfs.root.children["docs"] = Node("docs")
        self.vfs.root.children["docs"].children["guide"] = Node("guide")
        self.vfs.root.children["docs"].children["guide"].children[
            "reference"
        ] = Node("reference")
        self.shell = Shell(self.vfs)

    def test_prompt_contains_vfs_name(self):
        """Проверяет, что приглашение отображает имя VFS."""
        self.assertEqual(self.shell.prompt, "user@test-vfs:~$")

    def test_ls_and_cd(self):
        """Проверяет список файлов и переход в каталог."""
        self.assertIn("docs", self.shell.execute("ls")[0])
        self.assertEqual(self.shell.execute("cd docs")[0], "/docs")

    def test_head_reads_requested_lines(self):
        """Проверяет команду head с явным числом строк."""
        self.assertEqual(
            self.shell.execute("head -n 2 notes.txt")[0],
            "first\nsecond",
        )

    def test_head_uses_default_line_count(self):
        """Проверяет стандартный режим head без параметра -n."""
        self.assertEqual(
            self.shell.execute("head notes.txt"),
            ("first\nsecond\nthird", False),
        )

    def test_quoted_path_with_spaces(self):
        """Проверяет выполнение команды с путём в кавычках."""
        self.assertEqual(
            self.shell.execute('head -n 1 "notes with spaces.txt"'),
            ("first spaced line", False),
        )

    def test_uniq_removes_adjacent_duplicates(self):
        """Проверяет удаление только соседних повторяющихся строк."""
        self.assertEqual(
            self.shell.execute("uniq duplicates.txt")[0],
            "one\ntwo\nthree",
        )

    def test_uname_reports_host_system(self):
        """Проверяет, что uname возвращает имя ОС хоста."""
        self.assertEqual(
            self.shell.execute("uname"),
            (platform.system(), False),
        )

    def test_copy_changes_only_memory(self):
        """Проверяет копирование файла внутри виртуальной системы."""
        result = self.shell.execute("cp notes.txt copy.txt")
        self.assertEqual(result, ("", False))
        self.assertEqual(
            self.vfs.resolve("copy.txt").data,
            self.vfs.resolve("notes.txt").data,
        )

    def test_copy_rejects_directory_into_itself(self):
        """Проверяет запрет копирования каталога в его подкаталог."""
        with self.assertRaisesRegex(ShellError, "внутрь самого себя"):
            self.vfs.copy("docs", "docs/guide/reference/new-copy")

    def test_quotes_and_syntax_errors(self):
        """Проверяет кавычки, комментарии и ошибки парсера."""
        output, _ = self.shell.execute('ls "missing folder"')
        self.assertIn("missing folder", output)
        self.assertEqual(self.shell.execute("# comment"), ("", False))
        self.assertIn("синтаксиса", self.shell.execute('ls "broken')[0])

    def test_commands_report_invalid_arguments(self):
        """Проверяет сообщения об ошибке при неверном числе аргументов."""
        for command in (
            "ls one two",
            "cd one two",
            "head -n invalid notes.txt",
            "uniq",
            "uname extra",
            "cp notes.txt",
            "exit now",
        ):
            output, should_exit = self.shell.execute(command)
            self.assertIn("ошибка", output)
            self.assertFalse(should_exit)

    def test_unknown_command_and_exit(self):
        """Проверяет неизвестную команду и завершение оболочки."""
        self.assertIn(
            "команда не найдена",
            self.shell.execute("unknown-command")[0],
        )
        self.assertEqual(self.shell.execute("exit now")[1], False)
        self.assertEqual(
            self.shell.execute("exit"), ("Выход из эмулятора", True)
        )

    def test_loads_zip_without_extracting_files(self):
        """Проверяет загрузку файлов и вложенных каталогов из ZIP."""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = pathlib.Path(temp_dir) / "sample.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "docs/guide/reference/readme.txt",
                    "Привет\n".encode("utf-8"),
                )
                archive.writestr("raw.bin", b"\x00\xff")

            vfs = VirtualFileSystem()
            vfs.load_zip(archive_path)

        self.assertEqual(
            vfs.resolve("docs/guide/reference/readme.txt").data,
            "Привет\n".encode("utf-8"),
        )
        self.assertEqual(vfs.resolve("raw.bin").data, b"\x00\xff")

    def test_rejects_parent_paths_in_archive(self):
        """Проверяет отклонение путей за пределами корня VFS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = pathlib.Path(temp_dir) / "unsafe.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("../outside.txt", "unsafe")

            with self.assertRaises(ShellError):
                VirtualFileSystem().load_zip(archive_path)


if __name__ == "__main__":
    unittest.main()
