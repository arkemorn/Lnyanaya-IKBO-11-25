"""Создаёт ZIP-архивы с демонстрационной виртуальной системой."""

import argparse
import zipfile

MINIMAL_FILES = {
    "notes.txt": "Первая строка\nВторая строка\nТретья строка\n",
}
MULTIPLE_FILES = {
    **MINIMAL_FILES,
    "duplicates.txt": "alpha\nalpha\nbeta\nbeta\ngamma\n",
    "notes with spaces.txt": (
        "first spaced line\nsecond spaced line\nthird spaced line\n"
    ),
}
NESTED_FILES = {
    **MULTIPLE_FILES,
    "docs/guide/reference/readme.txt": (
        "Файл в каталоге третьего уровня.\n"
    ),
    "docs/guide/reference/notes.txt": "одна\nодна\nдве\nдве\nтри\n",
}
PROFILES = {
    "minimal": MINIMAL_FILES,
    "multiple": MULTIPLE_FILES,
    "nested": NESTED_FILES,
}


def parse_args(argv=None):
    """Разбирает параметры создания демонстрационного архива."""
    parser = argparse.ArgumentParser(
        description="Создать ZIP с демонстрационной виртуальной ФС"
    )
    parser.add_argument(
        "--profile", choices=tuple(PROFILES), default="minimal"
    )
    parser.add_argument("--output", required=True, help="путь к ZIP-архиву")
    return parser.parse_args(argv)


def create_archive(output_path, profile):
    """Записывает выбранный набор текстовых файлов в ZIP-архив."""
    with zipfile.ZipFile(
        output_path, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for filename, content in PROFILES[profile].items():
            archive.writestr(filename, content.encode("utf-8"))


def main(argv=None):
    """Создаёт архив и возвращает код завершения процесса."""
    args = parse_args(argv)
    create_archive(args.output, args.profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
