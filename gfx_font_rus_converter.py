import re
import sys
from pathlib import Path


# ============================================================
# Настройки
# ============================================================

NEW_FIRST = 0x20
NEW_LAST  = 0xBF


# ============================================================
# Соответствие:
#
# НОВАЯ ПОЗИЦИЯ -> СТАРАЯ ПОЗИЦИЯ
#
# Исходный шрифт содержит кириллицу в CP1251:
#
# C0-DF = А-Я
# E0-FF = а-я
#
# Новая позиция соответствует второму байту UTF-8:
#
# D0 90-D0 AF = А-Я
# D0 B0-D0 BF = а-п
# D1 80-D1 8F = р-я
# ============================================================

RUSSIAN_MAPPING = {

    # --------------------------------------------------------
    # Р - Я
    # UTF-8: D1 80 ... D1 8F
    # --------------------------------------------------------

    0x80: 0xF0,  # р
    0x81: 0xF1,  # с
    0x82: 0xF2,  # т
    0x83: 0xF3,  # у
    0x84: 0xF4,  # ф
    0x85: 0xF5,  # х
    0x86: 0xF6,  # ц
    0x87: 0xF7,  # ч
    0x88: 0xF8,  # ш
    0x89: 0xF9,  # щ
    0x8A: 0xFA,  # ъ
    0x8B: 0xFB,  # ы
    0x8C: 0xFC,  # ь
    0x8D: 0xFD,  # э
    0x8E: 0xFE,  # ю
    0x8F: 0xFF,  # я


    # --------------------------------------------------------
    # А - Я
    # UTF-8: D0 90 ... D0 AF
    # --------------------------------------------------------

    0x90: 0xC0,  # А
    0x91: 0xC1,  # Б
    0x92: 0xC2,  # В
    0x93: 0xC3,  # Г
    0x94: 0xC4,  # Д
    0x95: 0xC5,  # Е
    0x96: 0xC6,  # Ж
    0x97: 0xC7,  # З
    0x98: 0xC8,  # И
    0x99: 0xC9,  # Й
    0x9A: 0xCA,  # К
    0x9B: 0xCB,  # Л
    0x9C: 0xCC,  # М
    0x9D: 0xCD,  # Н
    0x9E: 0xCE,  # О
    0x9F: 0xCF,  # П
    0xA0: 0xD0,  # Р
    0xA1: 0xD1,  # С
    0xA2: 0xD2,  # Т
    0xA3: 0xD3,  # У
    0xA4: 0xD4,  # Ф
    0xA5: 0xD5,  # Х
    0xA6: 0xD6,  # Ц
    0xA7: 0xD7,  # Ч
    0xA8: 0xD8,  # Ш
    0xA9: 0xD9,  # Щ
    0xAA: 0xDA,  # Ъ
    0xAB: 0xDB,  # Ы
    0xAC: 0xDC,  # Ь
    0xAD: 0xDD,  # Э
    0xAE: 0xDE,  # Ю
    0xAF: 0xDF,  # Я


    # --------------------------------------------------------
    # а - п
    # UTF-8: D0 B0 ... D0 BF
    # --------------------------------------------------------

    0xB0: 0xE0,  # а
    0xB1: 0xE1,  # б
    0xB2: 0xE2,  # в
    0xB3: 0xE3,  # г
    0xB4: 0xE4,  # д
    0xB5: 0xE5,  # е
    0xB6: 0xE6,  # ж
    0xB7: 0xE7,  # з
    0xB8: 0xE8,  # и
    0xB9: 0xE9,  # й
    0xBA: 0xEA,  # к
    0xBB: 0xEB,  # л
    0xBC: 0xEC,  # м
    0xBD: 0xED,  # н
    0xBE: 0xEE,  # о
    0xBF: 0xEF,  # п
}


# ============================================================
# Найти массив GFXglyph
# ============================================================

def find_glyph_array(text):

    pattern = re.compile(
        r'(const\s+GFXglyph\s+(\w+)\s*\[\]\s*PROGMEM\s*=\s*\{)'
        r'(.*?)'
        r'(\};)',
        re.DOTALL
    )

    match = pattern.search(text)

    if not match:
        raise RuntimeError(
            "Не удалось найти массив GFXglyph[]."
        )

    return match


# ============================================================
# Разобрать GFXglyph[]
# ============================================================

def parse_glyphs(body):

    pattern = re.compile(
        r'\{'
        r'\s*([^{}]+?)'
        r'\s*\}'
    )

    glyphs = []

    for match in pattern.finditer(body):

        content = match.group(1)

        # Удаляем комментарии
        content = re.sub(
            r'//.*',
            '',
            content
        )

        values = [
            x.strip()
            for x in content.split(',')
            if x.strip()
        ]

        if len(values) != 6:
            continue

        glyphs.append(
            match.group(0)
        )

    return glyphs


# ============================================================
# Найти first/last в GFXfont
# ============================================================

def find_font_range(text):

    pattern = re.compile(
        r'const\s+GFXfont\s+\w+'
        r'.*?\{.*?'
        r'(0x[0-9A-Fa-f]+|\d+)'
        r'\s*,\s*'
        r'(0x[0-9A-Fa-f]+|\d+)'
        r'\s*,',
        re.DOTALL
    )

    match = pattern.search(text)

    if not match:
        raise RuntimeError(
            "Не удалось найти структуру GFXfont."
        )

    first = int(match.group(1), 0)
    last  = int(match.group(2), 0)

    return match, first, last


# ============================================================
# Изменить first / last
# ============================================================

def modify_font_range(text, match):

    new_text = (
        text[:match.start(1)]
        + f"0x{NEW_FIRST:02X}"
        + text[match.end(1):match.start(2)]
        + f"0x{NEW_LAST:02X}"
        + text[match.end(2):]
    )

    return new_text


# ============================================================
# Основная функция
# ============================================================

def convert(input_file, output_file):

    input_path = Path(input_file)
    output_path = Path(output_file)

    print()
    print("Adafruit GFX Russian font converter")
    print("-----------------------------------")
    print(f"Input : {input_path}")
    print(f"Output: {output_path}")
    print()

    # --------------------------------------------------------
    # Читаем файл как Latin-1.
    #
    # Это позволяет безопасно работать с .h, в котором
    # конвертер записал байты 0x80-0xFF непосредственно
    # в комментарии.
    # --------------------------------------------------------

    text = input_path.read_text(
        encoding="latin-1"
    )

    # --------------------------------------------------------
    # Находим GFXglyph[]
    # --------------------------------------------------------

    glyph_match = find_glyph_array(text)

    glyph_body = glyph_match.group(3)

    old_glyphs = parse_glyphs(glyph_body)

    if not old_glyphs:
        raise RuntimeError(
            "Не удалось разобрать GFXglyph[]."
        )

    print(
        f"Найдено glyph'ов: {len(old_glyphs)}"
    )

    # --------------------------------------------------------
    # Определяем first/last исходного шрифта
    # --------------------------------------------------------

    font_match, old_first, old_last = find_font_range(text)

    print(
        f"Исходный диапазон: "
        f"0x{old_first:02X} - 0x{old_last:02X}"
    )

    # --------------------------------------------------------
    # Проверяем, что исходный шрифт содержит все нужные
    # исходные glyph'ы.
    # --------------------------------------------------------

    def old_index(code):

        index = code - old_first

        if index < 0 or index >= len(old_glyphs):

            raise RuntimeError(
                f"В исходном шрифте отсутствует "
                f"glyph 0x{code:02X}."
            )

        return index

    # --------------------------------------------------------
    # Создаём НОВЫЙ массив только 0x20...0xBF.
    #
    # Это принципиально:
    #
    # всё после 0xBF физически исчезнет из файла.
    # --------------------------------------------------------

    new_glyphs = []

    for code in range(NEW_FIRST, NEW_LAST + 1):

        # Обычные символы ASCII и прочее,
        # которые уже находились на тех же позициях.

        if code not in RUSSIAN_MAPPING:

            index = old_index(code)

            new_glyphs.append(
                old_glyphs[index]
            )

        else:

            # Русская буква:
            # берём glyph из старой CP1251-позиции.

            source_code = RUSSIAN_MAPPING[code]

            index = old_index(source_code)

            new_glyphs.append(
                old_glyphs[index]
            )

    # --------------------------------------------------------
    # Проверяем количество
    # --------------------------------------------------------

    expected_count = NEW_LAST - NEW_FIRST + 1

    if len(new_glyphs) != expected_count:

        raise RuntimeError(
            f"Ошибка формирования массива: "
            f"получено {len(new_glyphs)}, "
            f"ожидалось {expected_count}."
        )

    print(
        f"Новый диапазон: "
        f"0x{NEW_FIRST:02X} - 0x{NEW_LAST:02X}"
    )

    print(
        f"Новых glyph'ов: {len(new_glyphs)}"
    )

    # --------------------------------------------------------
    # Формируем новый GFXglyph[]
    # --------------------------------------------------------

    new_body = "\n"

    for glyph in new_glyphs:

        new_body += (
            "    "
            + glyph
            + ",\n"
        )

    new_body += " "

    # --------------------------------------------------------
    # Заменяем старый массив новым
    # --------------------------------------------------------

    body_start = glyph_match.start(3)
    body_end   = glyph_match.end(3)

    new_text = (
        text[:body_start]
        + new_body
        + text[body_end:]
    )

    # --------------------------------------------------------
    # Меняем first/last
    # --------------------------------------------------------

    # После замены массива позиции в тексте могли измениться,
    # поэтому ищем GFXfont заново.

    font_match, _, _ = find_font_range(new_text)

    new_text = modify_font_range(
        new_text,
        font_match
    )

    # --------------------------------------------------------
    # Сохраняем UTF-8
    # --------------------------------------------------------

    output_path.write_text(
        new_text,
        encoding="utf-8"
    )

    # --------------------------------------------------------
    # Информация
    # --------------------------------------------------------

    print()
    print("Готово!")
    print()
    print(
        "Кириллица размещена по второму байту UTF-8:"
    )
    print(
        "  0x80-0x8F -> р-я"
    )
    print(
        "  0x90-0xAF -> А-Я"
    )
    print(
        "  0xB0-0xBF -> а-п"
    )
    print()
    print(
        "Glyph'ы после 0xBF удалены."
    )
    print(
        "Bitmap'ы не изменялись."
    )
    print(
        "bitmapOffset каждого glyph'а сохранён."
    )
    print()


# ============================================================
# Запуск
# ============================================================

def main():

    if len(sys.argv) < 2:

        print()
        print(
            "Использование:"
        )
        print(
            "  python gfx_rus_converter.py input.h"
        )
        print()
        print(
            "Или:"
        )
        print(
            "  python gfx_rus_converter.py input.h output.h"
        )
        print()

        return

    input_file = sys.argv[1]

    if len(sys.argv) >= 3:

        output_file = sys.argv[2]

    else:

        input_path = Path(input_file)

        output_file = (
            input_path.stem
            + "Rus"
            + input_path.suffix
        )

    try:

        convert(
            input_file,
            output_file
        )

    except Exception as error:

        print()
        print("ОШИБКА:")
        print(error)
        print()

        sys.exit(1)


if __name__ == "__main__":
    main()
