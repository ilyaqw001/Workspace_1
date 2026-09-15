#!/usr/bin/env python3
import sys
import os
import json
import pymupdf

CONFIG_FILE = "ocr_layout_config.json"

# Заводские параметры по умолчанию
DEFAULT_CONFIG = {
    "block_distance_threshold": 15.0,
    "strip_hyphens": True,
    "force_dpi": 150
}

def load_settings():
    """Считывает настройки из конфигуратора UI."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG

def find_any_true_type_font():
    """
    Динамически ищет первый попавшийся TrueType-шрифт в проброшенном каталоге.
    Исключает закладывание неверных жестких путей.
    """
    fonts_dir = "/usr/share/fonts"
    if not os.path.exists(fonts_dir):
        return None

    for root, _, files in os.walk(fonts_dir):
        for file in files:
            if file.lower().endswith(".ttf"):
                full_path = os.path.join(root, file)
                # Проверяем, что файл реально читается
                if os.path.isfile(full_path) and os.path.getsize(full_path) > 0:
                    return full_path
    return None

def process_pdf(input_pdf_path, output_pdf_path):
    # 1. Загрузка конфигурации из UI
    cfg = load_settings()
    block_threshold = cfg.get("block_distance_threshold", 15.0)
    strip_hyphens = cfg.get("strip_hyphens", True)
    render_dpi = cfg.get("force_dpi", 150)

    # 2. Динамический поиск шрифта в проброшенной системе
    font_file_path = find_any_true_type_font()
    if not font_file_path:
        print("[Ошибка] В папке /usr/share/fonts не найдено ни одного .ttf файла!", file=sys.stderr)
        print("Проверьте, корректно ли примонтирована папка шрифтов в Bubblewrap.", file=sys.stderr)
        return False

    print(f"[*] Успешно обнаружен рабочий шрифт: {font_file_path}")

    if not os.path.exists(input_pdf_path):
        print(f"[Ошибка] Входной файл '{input_pdf_path}' не существует!", file=sys.stderr)
        return False

    # 3. Инициализация документов
    doc = pymupdf.open(input_pdf_path)
    new_doc = pymupdf.open()
    total_pages = len(doc)
    print(f"[*] Обработка страниц процессором макета. Всего: {total_pages}")

    # Загружаем шрифт один раз для всех страниц - это гарантирует корректную CMap
    font = pymupdf.Font(fontfile=font_file_path)

    for page_num in range(total_pages):
        page = doc[page_num]
        rect = page.rect

        # Получаем детальную структуру распознанного текста
        page_dict = page.get_text("dict")

        # Создаем чистую растровую подложку
        pix = page.get_pixmap(dpi=render_dpi)
        new_page = new_doc.new_page(width=rect.width, height=rect.height)
        new_page.insert_image(rect, pixmap=pix)

        # 4. Обход блоков и интеллектуальная склейка строк
        for block in page_dict.get("blocks", []):
            if "lines" in block and block.get("type") == 0:
                lines = block["lines"]

                for i, line in enumerate(lines):
                    # Сборка текста текущей строки
                    line_text = "".join([span.get("text", "") for span in line.get("spans", [])])
                    if not line_text.strip():
                        continue

                    x0, y0, x1, y1 = line["bbox"]

                    has_next_line = (i < len(lines) - 1)
                    is_line_broken = False

                    # Проверяем зазор до следующей строки в блоке
                    if has_next_line:
                        next_line = lines[i + 1]
                        _, next_y0, _, _ = next_line["bbox"]

                        # Если зазор больше порога из UI, сохраняем жесткий разрыв
                        if (next_y0 - y1) > block_threshold:
                            is_line_broken = True

                    # Форматирование окончаний строк при склеивании
                    if has_next_line and not is_line_broken:
                        if strip_hyphens and line_text.endswith("-"):
                            line_text = line_text[:-1]  # Удаляем дефис переноса
                        else:
                            line_text += " "  # Склеиваем пробелом вместо разрыва строки \n

                    # Динамический расчет размера букв
                    font_size = max(6, min(14, y1 - y0))

                    # Накладываем невидимый текстовый слой с использованием предварительно загруженного шрифта
                    # Передача объекта Font гарантирует корректное создание CMap для кириллицы
                    new_page.insert_text(
                        pymupdf.Point(x0, y1 - 2),
                        line_text,
                        fontsize=font_size,
                        font=font,
                        render_mode=3
                    )

    # 5. Сохранение результата
    print("[*] Сохранение оптимизированного PDF файла...")
    new_doc.save(output_pdf_path, garbage=4, deflate=True)
    new_doc.close()
    doc.close()
    print(f"[+] Процесс завершен. Результат записан в: {output_pdf_path}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Использование: python3 fix_pdf_layout.py <входной.pdf> <выходной.pdf>", file=sys.stderr)
        sys.exit(1)

    # Строгие и точные индексы аргументов командной строки
    in_file = sys.argv[1]
    out_file = sys.argv[2]

    if not process_pdf(in_file, out_file):
        sys.exit(1)
