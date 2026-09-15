#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys

CONFIG_FILE = "ocr_layout_config.json"

# Дефолтные безопасные настройки
DEFAULT_CONFIG = {
    "block_distance_threshold": 15.0,
    "char_width_tolerance": 0.35,
    "line_height_tolerance": 0.25,
    "strip_hyphens": True,
    "force_dpi": 150,
    "use_embedded_font": "sans"
}

class ConfigApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Настройки OCR & Макетного процессора")
        self.root.geometry("620x540")
        self.root.resizable(False, False)

        # Стилизация под современный лаконичный UI
        style = ttk.Style()
        style.theme_use('clam')

        self.load_config()
        self.create_widgets()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()

    def create_widgets(self):
        # Главный контейнер с отступами
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        header = ttk.Label(main_frame, text="Параметры подготовки финального PDF", font=("Helvetica", 12, "bold"))
        header.pack(anchor=tk.W, pady=(0, 15))

        # --- ГРУППА 1: НАСТРОЙКИ СЕГМЕНТАЦИИ И СКЛЕИВАНИЯ ---
        seg_frame = ttk.LabelFrame(main_frame, text=" Настройки макета и склеивания блоков ", padding="10")
        seg_frame.pack(fill=tk.X, pady=(0, 10))

        # 1. Расстояние между логическими блоками
        self.add_setting_row(
            seg_frame, "Расстояние между блоками (pt):", "block_distance_threshold",
            "Порог по вертикали. Если расстояние между строками больше этого значения,\n"
            "они гарантированно делятся на разные абзацы. Помогает против склеивания\n"
            "разных тезисов или подписей к рисункам."
        )

        # 2. Допуск ширины символов (Char Tolerance)
        self.add_setting_row(
            seg_frame, "Допуск ширины символа (0.0 - 1.0):", "char_width_tolerance",
            "Регулирует склеивание букв в слова. Чем выше значение, тем агрессивнее\n"
            "склеиваются пробелы внутри одной строки. Помогает при разрывах в словах."
        )

        # 3. Допуск высоты строк
        self.add_setting_row(
            seg_frame, "Допуск высоты строк (0.0 - 1.0):", "line_height_tolerance",
            "Если межстрочный интервал колеблется в пределах этого коэффициента, строки\n"
            "считаются частью одного абзаца. Меньше значение — строже деление на абзацы."
        )

        # --- ГРУППА 2: ОБРАБОТКА ТЕКСТА И ОПТИМИЗАЦИЯ ---
        proc_frame = ttk.LabelFrame(main_frame, text=" Обработка текста и Рендеринг ", padding="10")
        proc_frame.pack(fill=tk.X, pady=(0, 15))

        # 4. Флаг удаления дефисов переноса
        self.add_checkbox_row(
            proc_frame, "Удалять дефисы при переносе слов:", "strip_hyphens",
            "Автоматически склеивает слова, разорванные знаком дефиса на конце строки\n"
            "(например, 'распоз-\nнавание' превратится в 'распознавание')."
        )

        # 5. Разрешение подложки DPI
        self.add_setting_row(
            proc_frame, "Разрешение подложки страниц (DPI):", "force_dpi",
            "DPI фонового изображения. 150 — быстро и легковесно. 300 — максимальное\n"
            "визуальное качество текста, но файл будет весить значительно больше."
        )

        # Переменные для хранения полей ввода
        self.vars = {}

        # Заполнение UI текущими данными
        self.refresh_ui_values()

        # Кнопки управления внизу
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        save_btn = ttk.Button(btn_frame, text="Сохранить конфигурацию", command=self.save_config)
        save_btn.pack(side=tk.RIGHT, padx=5)

        reset_btn = ttk.Button(btn_frame, text="Сбросить по умолчанию", command=self.reset_to_default)
        reset_btn.pack(side=tk.RIGHT, padx=5)

    def add_setting_row(self, parent, label_text, config_key, tooltip_text):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)

        lbl = ttk.Label(row, text=label_text, width=32, anchor=tk.W)
        lbl.pack(side=tk.LEFT)

        entry = ttk.Entry(row, width=8)
        entry.pack(side=tk.LEFT, padx=(0, 10))

        info_lbl = ttk.Label(row, text="❓", cursor="hand2", foreground="#0066cc")
        info_lbl.pack(side=tk.LEFT)
        info_lbl.bind("<Button-1>", lambda e: messagebox.showinfo("Подсказка", tooltip_text))

        if not hasattr(self, 'entries'): self.entries = {}
        self.entries[config_key] = entry

    def add_checkbox_row(self, parent, label_text, config_key, tooltip_text):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)

        var = tk.BooleanVar()
        chk = ttk.Checkbutton(row, text=label_text, variable=var)
        chk.pack(side=tk.LEFT, padx=(0, 10))

        info_lbl = ttk.Label(row, text="❓", cursor="hand2", foreground="#0066cc")
        info_lbl.pack(side=tk.LEFT)
        info_lbl.bind("<Button-1>", lambda e: messagebox.showinfo("Подсказка", tooltip_text))

        if not hasattr(self, 'checkboxes'): self.checkboxes = {}
        self.checkboxes[config_key] = var

    def refresh_ui_values(self):
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(self.config.get(key, DEFAULT_CONFIG[key])))
        for key, var in self.checkboxes.items():
            var.set(bool(self.config.get(key, DEFAULT_CONFIG[key])))

    def save_config(self):
        new_config = {}
        try:
            for key, entry in self.entries.items():
                val = entry.get()
                if key == "force_dpi":
                    new_config[key] = int(val)
                else:
                    new_config[key] = float(val)

            for key, var in self.checkboxes.items():
                new_config[key] = var.get()

            new_config["use_embedded_font"] = self.config.get("use_embedded_font", "sans")

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)

            messagebox.showinfo("Успех", f"Конфигурация успешно сохранена в файл {CONFIG_FILE}!")
        except ValueError:
            messagebox.showerror("Ошибка", "Пожалуйста, введите корректные числовые значения в поля настроек.")

    def reset_to_default(self):
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите сбросить все параметры на заводские?"):
            self.config = DEFAULT_CONFIG.copy()
            self.refresh_ui_values()

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigApp(root)
    root.mainloop()
