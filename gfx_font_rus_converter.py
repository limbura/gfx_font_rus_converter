import re
import sys
from pathlib import Path


# ============================================================
# CP1251 -> специальная раскладка AdafruitGFXRusFonts
# ============================================================

RUSSIAN_MAPPING = {
    # Заглавные А-Я
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

    # Строчные а-п
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

    # Строчные р-я
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
}


# ============================================================
# Поиск массива GFXglyph
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
            "Не удалось найти массив GFXglyph[]"
        )

    return match


# ============================================================
# Разбор отдельных записей GFXglyph
#
# Формат:
#
# { bitmapOffset, width, height, xAdvance, xOffset, yOffset }
#
# ============================================================

def parse_glyphs(body):

    pattern = re.compile(
        r'\{'
        r'\s*([^{}]+?)'
        r'\s*\}'
    )

    matches = list(pattern.finditer(body))

    glyphs = []

    for match in matches:

        content = match.group(1)

        # Убираем комментарии
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
# Поиск GFXfont
# ============================================================

def modify_gfxfont(text, first, last):

    pattern = re.compile(
        r'(\{\s*'
        r'\(uint8_t\s*\*\)\w+\s*,'
        r'\s*\(GFXglyph\s*\*\)\w+\s*,'
        r'\s*)'
        r'(0x[0-9A-Fa-f]+|\d+)'
        r'(\s*,\s*)'
        r'(0x[0-9A-Fa-f]+|\d+)'
        r'(\s*,)',
        re.DOTALL
    )

    match = pattern.search(text)

    if not match:
        raise RuntimeError(
            "Не удалось найти структуру GFXfont"
        )

    new_text = (
        text[:match.start()]
        + match.group(1)
        + f"0x{first:02X}"
        + match.group(3)
        + f"0x{last:02X}"
        + match.group(5)
        + text[match.end():]
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

    text = input_path.read_text(
        encoding="latin-1"
    )

    # --------------------------------------------------------
    # Ищем GFXglyph[]
    # --------------------------------------------------------

    match = find_glyph_array(text)

    body_start = match.start(3)
    body_end = match.end(3)

    glyph_body = match.group(3)

    glyphs = parse_glyphs(glyph_body)

    if not glyphs:
        raise RuntimeError(
            "Не удалось разобрать GFXglyph[]"
        )

    print(f"Найдено glyph'ов: {len(glyphs)}")

    # --------------------------------------------------------
    # Определяем first.
    #
    # Обычно это 0x20.
    # --------------------------------------------------------

    font_pattern = re.compile(
        r'const\s+GFXfont\s+\w+'
        r'.*?\{.*?'
        r'0x([0-9A-Fa-f]+)'
        r'\s*,'
        r'\s*0x([0-9A-Fa-f]+)',
        re.DOTALL
    )

    font_match = font_pattern.search(text)

    if not font_match:
        raise RuntimeError(
            "Не удалось определить first/last GFXfont"
        )

    old_first = int(
        font_match.group(1),
        16
    )

    old_last = int(
        font_match.group(2),
        16
    )

    print(
        f"Исходный диапазон: "
        f"0x{old_first:02X} - 0x{old_last:02X}"
    )

    # --------------------------------------------------------
    # Проверяем, что в массиве вообще есть CP1251 C0-FF
    # --------------------------------------------------------

    def index_for_code(code):
        return code - old_first

    required_codes = list(
        RUSSIAN_MAPPING.values()
    )

    for code in required_codes:

        index = index_for_code(code)

        if index < 0 or index >= len(glyphs):

            raise RuntimeError(
                f"В шрифте отсутствует glyph "
                f"0x{code:02X}. "
                f"Найден диапазон "
                f"0x{old_first:02X}-"
                f"0x{old_last:02X}."
            )

    # --------------------------------------------------------
    # Создаём копию массива
    # --------------------------------------------------------

    new_glyphs = glyphs.copy()

    # --------------------------------------------------------
    # Переставляем русские glyph'ы
    #
    # destination = source
    #
    # Например:
    #
    # new[0x90] = old[0xC0]
    #
    # --------------------------------------------------------

    for destination, source in RUSSIAN_MAPPING.items():

        destination_index = index_for_code(
            destination
        )

        source_index = index_for_code(
            source
        )

        new_glyphs[destination_index] = (
            glyphs[source_index]
        )

    # --------------------------------------------------------
    # Формируем новый массив
    # --------------------------------------------------------

    new_body = "\n"

    for glyph in new_glyphs:

        new_body += (
            "  "
            + glyph
            + ",\n"
        )

    new_body += " "

    new_text = (
        text[:body_start]
        + new_body
        + text[body_end:]
    )

    # --------------------------------------------------------
    # Меняем диапазон GFXfont
    #
    # Он должен включать 0x20...0xBF
    # --------------------------------------------------------

    new_text = modify_gfxfont(
        new_text,
        old_first,
        0xBF
    )

    # --------------------------------------------------------
    # Сохраняем
    # --------------------------------------------------------

    output_path.write_text(
        new_text,
        encoding="utf-8"
    )

    print()
    print("Готово!")
    print()
    print(
        "Русская раскладка установлена:"
    )

    for destination, source in RUSSIAN_MAPPING.items():

        print(
            f"  0x{source:02X} -> "
            f"0x{destination:02X}"
        )

    print()
    print(
        "Bitmap'ы не изменялись."
    )
    print(
        "GFXglyph bitmapOffset не изменялись."
    )
    print()


# ============================================================
# Точка входа
# ============================================================

def main():

    if len(sys.argv) < 2:

        print(
            "Использование:"
        )

        print(
            "  python gfx_rus_converter.py "
            "input.h [output.h]"
        )

        print()

        print(
            "Например:"
        )

        print(
            "  python gfx_rus_converter.py "
            "BahnschriftLight18.h "
            "BahnschriftLight18Rus.h"
        )

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