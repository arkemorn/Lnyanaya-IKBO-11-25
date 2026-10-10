"""Тесты основных возможностей оболочки."""
import base64
import csv
import pathlib
import tempfile
import unittest
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from shell import Shell, ShellError, VirtualFileSystem


class ShellTests(unittest.TestCase):
    def setUp(self):
        self.vfs = VirtualFileSystem()
        self.vfs.root.children["hello.txt"] = __import__("shell").Node(
            "hello.txt", "file", "first\nsecond\nthird"
        )
        self.vfs.root.children["docs"] = __import__("shell").Node("docs")
        self.shell = Shell(self.vfs)

    def test_quotes(self):
        self.assertEqual(self.shell.execute('ls "hello world"')[0], "ошибка: нет такого файла или каталога: hello world")

    def test_ls_and_cd(self):
        self.assertIn("docs", self.shell.execute("ls")[0])
        self.assertEqual(self.shell.execute("cd docs")[0], "/docs")

    def test_tail(self):
        self.assertEqual(self.shell.execute("tail hello.txt")[0], "first\nsecond\nthird")

    def test_uname_du(self):
        self.assertIn("VFS-Shell", self.shell.execute("uname")[0])
        self.assertEqual(self.shell.execute("du hello.txt")[0], "18\thello.txt")

    def test_cp_mv(self):
        self.assertEqual(self.shell.execute("cp hello.txt copy.txt"), ("", False))
        self.assertEqual(self.shell.execute("mv copy.txt moved.txt"), ("", False))
        self.assertEqual(self.shell.execute("ls")[0].count("moved.txt"), 1)

    def test_errors_and_exit(self):
        self.assertIn("команда не найдена", self.shell.execute("badcommand")[0])
        self.assertIn("лишние аргументы", self.shell.execute("exit now")[0])
        self.assertEqual(self.shell.execute("exit"), ("logout", True))

    def test_conf_dump(self):
        self.assertIn("vfs_path=", self.shell.execute("conf-dump")[0])

    def test_csv_load(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / "vfs.csv"
            encoded = base64.b64encode(b"hello").decode()
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=["path", "type", "content_base64"])
                writer.writeheader()
                writer.writerow({"path": "folder", "type": "dir", "content_base64": ""})
                writer.writerow({"path": "folder/a.txt", "type": "file", "content_base64": encoded})
            vfs = VirtualFileSystem()
            vfs.load_csv(path)
            self.assertEqual(vfs.resolve("/folder/a.txt").data, "hello")


if __name__ == "__main__":
    unittest.main()
