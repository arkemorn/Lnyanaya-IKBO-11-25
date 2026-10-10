"""Графический интерфейс эмулятора."""
import argparse
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from shell import Shell, ShellError, VirtualFileSystem


def parse_args():
    parser = argparse.ArgumentParser(description="Эмулятор оболочки VFS")
    parser.add_argument("--vfs", help="путь к CSV-файлу виртуальной системы")
    parser.add_argument("--script", help="путь к стартовому скрипту команд")
    parser.add_argument("--prompt", default="user@vfs:~$", help="приглашение")
    return parser.parse_args()


class Window:
    """Окно терминала с историей команд."""
    def __init__(self, root, shell):
        self.root = root
        self.shell = shell
        self.root.title(f"VFS — Эмулятор оболочки")
        self.root.geometry("850x560")
        self.root.configure(bg="#111827")
        self.output = ScrolledText(
            root, bg="#111827", fg="#e5e7eb", insertbackground="#e5e7eb",
            font=("Consolas", 11), wrap=tk.WORD, relief=tk.FLAT,
            padx=14, pady=12, state=tk.DISABLED,
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 4))
        bottom = tk.Frame(root, bg="#111827")
        bottom.pack(fill=tk.X, padx=12, pady=(4, 12))
        tk.Label(
            bottom, text=self.shell.prompt, bg="#111827", fg="#34d399",
            font=("Consolas", 11),
        ).pack(side=tk.LEFT)
        self.entry = tk.Entry(
            bottom, bg="#1f2937", fg="#f9fafb", insertbackground="#f9fafb",
            font=("Consolas", 11), relief=tk.FLAT,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), ipady=7)
        self.entry.bind("<Return>", self.on_enter)
        self.entry.focus_set()
        self.write("Эмулятор запущен. Команды: ls, cd, tail, uname, du, cp, mv, conf-dump, exit")
        if self.shell.script_path != "(не задан)":
            self.run_script(self.shell.script_path)

    def write(self, text):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + ("" if text.endswith("\n") else "\n"))
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def run_script(self, path):
        try:
            with open(path, encoding="utf-8") as stream:
                for number, raw in enumerate(stream, start=1):
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    self.write(f"{self.shell.prompt} {line}")
                    result, should_exit = self.shell.execute(line)
                    if result:
                        self.write(result)
                    if result.startswith("ошибка:") or result.startswith("ошибка синтаксиса:"):
                        self.write(f"Скрипт остановлен: ошибка в строке {number}.")
                        break
                    if should_exit:
                        break
        except OSError as exc:
            self.write(f"Не удалось прочитать стартовый скрипт: {exc}")

    def on_enter(self, _event=None):
        line = self.entry.get()
        self.entry.delete(0, tk.END)
        self.write(f"{self.shell.prompt} {line}")
        result, should_exit = self.shell.execute(line)
        if result:
            self.write(result)
        if should_exit:
            self.root.after(150, self.root.destroy)


def main():
    args = parse_args()
    vfs = VirtualFileSystem()
    if args.vfs:
        try:
            vfs.load_csv(args.vfs)
        except (OSError, ShellError) as exc:
            raise SystemExit(f"Ошибка загрузки VFS: {exc}")
    shell = Shell(vfs, args.vfs, args.script, args.prompt)
    print("Параметры запуска:")
    print(shell.conf_dump())
    root = tk.Tk()
    Window(root, shell)
    root.mainloop()


if __name__ == "__main__":
    main()
