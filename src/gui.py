
"""Графический интерфейс эмулятора оболочки."""
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from shell import Shell


class Window:
    def __init__(self, root):
        self.root = root
        self.shell = Shell()

        self.root.title("VFS — Эмулятор оболочки")
        self.root.geometry("800x500")
        self.root.configure(bg="#111827")

        self.output = ScrolledText(
            root,
            bg="#111827",
            fg="#e5e7eb",
            insertbackground="#e5e7eb",
            font=("Consolas", 11),
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=14,
            pady=12,
            state=tk.DISABLED,
        )
        self.output.pack(
            fill=tk.BOTH, expand=True, padx=10, pady=(10, 4)
        )

        bottom = tk.Frame(root, bg="#111827")
        bottom.pack(fill=tk.X, padx=12, pady=(4, 12))

        tk.Label(
            bottom,
            text="user@vfs:~$",
            bg="#111827",
            fg="#34d399",
            font=("Consolas", 11),
        ).pack(side=tk.LEFT)

        self.entry = tk.Entry(
            bottom,
            bg="#1f2937",
            fg="#f9fafb",
            insertbackground="#f9fafb",
            font=("Consolas", 11),
            relief=tk.FLAT,
        )
        self.entry.pack(
            side=tk.LEFT, fill=tk.X, expand=True,
            padx=(8, 0), ipady=7
        )
        self.entry.bind("<Return>", self.on_enter)
        self.entry.focus_set()

        self.write(
            "Эмулятор запущен. Команды: ls, cd, exit"
        )

    def write(self, text):
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, text + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def on_enter(self, _event=None):
        line = self.entry.get()
        self.entry.delete(0, tk.END)

        self.write(f"user@vfs:~$ {line}")
        result, should_exit = self.shell.execute(line)

        if result:
            self.write(result)

        if should_exit:
            self.root.after(150, self.root.destroy)


def main():
    root = tk.Tk()
    Window(root)
    root.mainloop()


if __name__ == "__main__":
    main()