"""Точка входа для консольного эмулятора командной оболочки."""

import argparse
import sys

from .shell import Shell, ShellError, VirtualFileSystem

MEMORY_PATH = "(память)"
UNSET_PATH = "(не задан)"
SUCCESS = 0
FAILURE = 1


def parse_args(argv=None):
    """Разбирает параметры запуска эмулятора."""
    parser = argparse.ArgumentParser(
        description="Консольный эмулятор оболочки с виртуальной ФС"
    )
    parser.add_argument("--vfs", dest="vfs_path", help="путь к ZIP-архиву")
    parser.add_argument(
        "--script", dest="script_path", help="путь к стартовому скрипту"
    )
    return parser.parse_args(argv)


def print_configuration(args):
    """Печатает заданные пути в формате ключ=значение."""
    vfs_path = args.vfs_path or MEMORY_PATH
    script_path = args.script_path or UNSET_PATH
    print("Параметры запуска:")
    print(f"vfs_path={vfs_path}")
    print(f"script_path={script_path}")


def execute_command(shell, line):
    """Выполняет команду, печатает ответ и возвращает признак выхода."""
    result, should_exit = shell.execute(line)
    if result:
        print(result)
    return should_exit


def run_command(shell, line):
    """Показывает команду сценария и выполняет её."""
    print(f"{shell.prompt} {line}")
    return execute_command(shell, line)


def run_startup_script(shell, script_path):
    """Выполняет команды из файла с поддержкой строк-комментариев."""
    with open(script_path, encoding="utf-8-sig") as stream:
        for raw_line in stream:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if run_command(shell, line):
                return True
    return False


def run_interactive(shell):
    """Читает и выполняет команды в интерактивном режиме."""
    while True:
        try:
            line = input(f"{shell.prompt} ")
        except EOFError:
            print()
            return
        if execute_command(shell, line):
            return


def load_vfs(vfs_path):
    """Создаёт VFS и загружает архив, если он был указан."""
    vfs = VirtualFileSystem()
    if vfs_path:
        vfs.load_zip(vfs_path)
    return vfs


def main(argv=None):
    """Запускает эмулятор и возвращает код завершения процесса."""
    args = parse_args(argv)
    print_configuration(args)
    try:
        vfs = load_vfs(args.vfs_path)
    except (OSError, ShellError) as exc:
        print(f"ошибка загрузки VFS: {exc}", file=sys.stderr)
        return FAILURE

    shell = Shell(vfs)

    if args.script_path:
        try:
            should_exit = run_startup_script(shell, args.script_path)
        except OSError as exc:
            print(f"ошибка чтения стартового скрипта: {exc}", file=sys.stderr)
            return FAILURE
        if should_exit:
            return SUCCESS

    run_interactive(shell)
    return SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
