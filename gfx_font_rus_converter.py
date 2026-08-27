import re
import sys
from pathlib import Path


# ============================================================
# НАСТРОЙКИ
# ============================================================

FIRST_CHAR = 0x20
LAST_CHAR = 0xBF


# ============================================================
# КИРИЛЛИЦА
#
# Формат:
#
#   НОВЫЙ КОД -> ИСХОДНЫЙ КОД
#
# То есть:
#
#   0x80 <- 0xF0   р
#   ...
#   0x8F <- 0xFF   я
#
#   0x90 <- 0xC0   А
#   ...
#   0xBF <- 0xEF   п
# ============================================================

RUSSIAN_MAPPING = {

    # р-я
    0x80: 0xF0,
    0x81: 0xF1,
    0x82: 0xF2,
    0x83: 0xF3,
    0x84: 0xF4,
    0x85: 0xF5,
    0x86: 0xF6,
    0x87: 0xF7,
    0x88: 0xF8,
    0x89: 0xF9,
    0x8A: 0xFA,
    0x8B: 0xFB,
    0x8C: 0xFC,
    0x8D: 0xFD,
    0x8E: 0xFE,
    0x8F: 0xFF,

    # А-Я
    0x90: 0xC0,
    0x91: 0xC1,
    0x92: 0xC2,
    0x93: 0xC3,
    0x94: 0xC4,
    0x95: 0xC5,
    0x96: 0xC6,
    0x97: 0xC7,
    0x98: 0xC8,
    0x99: 0xC9,
    0x9A: 0xCA,
    0x9B: 0xCB,
    0x9C: 0xCC,
    0x9D: 0xCD,
    0x9E: 0xCE,
    0x9F: 0xCF,
    0xA0: 0xD0,
    0xA1: 0xD1,
    0xA2: 0xD2,
    0xA3: 0xD3,
    0xA4: 0xD4,
    0xA5: 0xD5,
    0xA6: 0xD6,
    0xA7: 0xD7,
    0xA8: 0xD8,
    0xA9: 0xD9,
    0xAA: 0xDA,
    0xAB: 0xDB,
    0xAC: 0xDC,
    0xAD: 0xDD,
    0xAE: 0xDE,
    0xAF: 0xDF,

    # а-п
    0xB0: 0xE0,
    0xB1: 0xE1,
    0xB2: 0xE2,
    0xB3: 0xE3,
    0xB4: 0xE4,
    0xB5: 0xE5,
    0xB6: 0xE6,
    0xB7: 0xE7,
    0xB8: 0xE8,
    0xB9: 0xE9,
    0xBA: 0xEA,
    0xBB: 0xEB,
    0xBC: 0xEC,
    0xBD: 0xED,
    0xBE: 0xEE,
    0xBF: 0xEF,
}


# ============================================================
# УДАЛЕНИЕ КОММЕНТАРИЕВ
# ============================================================

def remove_comments(text):
    """
    Удаляет // и /* */ комментарии.

    Нужно только для надёжного разбора массивов.
    Оригинальный текст при этом не изменяется.
    """

    text = re.sub(
        r"//.*?$",
        "",
        text,
        flags=re.MULTILINE
    )

    text = re.sub(
        r"/\*.*?\*/",
        "",
        text,
        flags=re.DOTALL
    )

    return text


# ============================================================
# ПОИСК BITMAPS
# ============================================================

def find_bitmaps(text):

    match = re.search(
        r"const\s+uint8_t\s+(\w+Bitmaps)\s*\[\]\s*"
        r"PROGMEM\s*=\s*\{(.*?)\};",
        text,
        re.DOTALL
    )

    if not match:
        raise RuntimeError(
            "Не удалось найти массив Bitmaps[]."
        )

    name = match.group(1)
    body = match.group(2)

    clean_body = remove_comments(body)

    tokens = re.findall(
        r"0[xX][0-9A-Fa-f]+|\d+",
        clean_body
    )

    values = [
        int(token, 0)
        for token in tokens
    ]

    return match, name, values


# ============================================================
# ПОИСК GLYPHS
# ============================================================

def find_glyphs(text):

    match = re.search(
        r"const\s+GFXglyph\s+(\w+Glyphs)\s*\[\]\s*"
        r"PROGMEM\s*=\s*\{(.*?)\};",
        text,
        re.DOTALL
    )

    if not match:
        raise RuntimeError(
            "Не удалось найти массив GFXglyph[]."
        )

    name = match.group(1)
    body = match.group(2)

    clean_body = remove_comments(body)

    pattern = re.compile(
        r"\{\s*"
        r"(-?\d+)\s*,\s*"
        r"(-?\d+)\s*,\s*"
        r"(-?\d+)\s*,\s*"
        r"(-?\d+)\s*,\s*"
        r"(-?\d+)\s*,\s*"
        r"(-?\d+)\s*"
        r"\}"
    )

    glyphs = []

    for m in pattern.finditer(clean_body):

        glyphs.append(
            tuple(
                int(x)
                for x in m.groups()
            )
        )

    if not glyphs:
        raise RuntimeError(
            "Не удалось разобрать GFXglyph[]."
        )

    return match, name, glyphs


# ============================================================
# РАЗМЕР BITMAP GLYPH
# ============================================================

def glyph_bitmap_size(glyph):

    """
    В Adafruit GFX bitmap полностью bit-packed.

    Поэтому:

        width * height

    бит округляется вверх до целого байта.
    """

    _, width, height, _, _, _ = glyph

    bits = width * height

    return (bits + 7) // 8


# ============================================================
# ПОЛУЧЕНИЕ GLYPH
# ============================================================

def get_glyph(glyphs, first, code):

    index = code - first

    if index < 0 or index >= len(glyphs):

        raise RuntimeError(
            f"Glyph 0x{code:02X} отсутствует."
        )

    return glyphs[index]


# ============================================================
# ФОРМИРОВАНИЕ НОВОГО BITMAP
# ============================================================

def rebuild_bitmaps(
    source_glyphs,
    source_first,
    source_bitmaps
):

    new_bitmaps = []
    new_glyphs = []

    print()
    print("Rebuilding Bitmaps[]...")
    print()

    for new_code in range(
        FIRST_CHAR,
        LAST_CHAR + 1
    ):

        # ----------------------------------------------------
        # Определяем исходный код
        # ----------------------------------------------------

        if new_code < 0x80:

            source_code = new_code

        else:

            source_code = RUSSIAN_MAPPING.get(
                new_code
            )

            if source_code is None:

                raise RuntimeError(
                    f"Нет mapping для "
                    f"0x{new_code:02X}"
                )

        # ----------------------------------------------------
        # Получаем исходный glyph
        # ----------------------------------------------------

        source_glyph = get_glyph(
            source_glyphs,
            source_first,
            source_code
        )

        (
            old_offset,
            width,
            height,
            xadvance,
            xoffset,
            yoffset
        ) = source_glyph

        # ----------------------------------------------------
        # Определяем размер bitmap
        # ----------------------------------------------------

        bitmap_size = glyph_bitmap_size(
            source_glyph
        )

        old_end = (
            old_offset
            + bitmap_size
        )

        # ----------------------------------------------------
        # Проверяем исходный bitmap
        # ----------------------------------------------------

        if old_offset < 0:

            raise RuntimeError(
                f"Glyph 0x{source_code:02X} "
                f"имеет отрицательный bitmapOffset."
            )

        if old_end > len(source_bitmaps):

            raise RuntimeError(
                f"Glyph 0x{source_code:02X} "
                f"выходит за пределы Bitmaps[]: "
                f"offset={old_offset}, "
                f"size={bitmap_size}, "
                f"end={old_end}, "
                f"bitmap size={len(source_bitmaps)}"
            )

        # ----------------------------------------------------
        # Копируем bitmap
        # ----------------------------------------------------

        bitmap = source_bitmaps[
            old_offset:old_end
        ]

        # ----------------------------------------------------
        # Новый offset
        # ----------------------------------------------------

        new_offset = len(
            new_bitmaps
        )

        # ----------------------------------------------------
        # Добавляем bitmap в новый массив
        # ----------------------------------------------------

        new_bitmaps.extend(
            bitmap
        )

        # ----------------------------------------------------
        # Создаём новый glyph
        #
        # Все параметры кроме bitmapOffset
        # остаются неизменными.
        # ----------------------------------------------------

        new_glyph = (
            new_offset,
            width,
            height,
            xadvance,
            xoffset,
            yoffset
        )

        new_glyphs.append(
            new_glyph
        )

        print(
            f"0x{new_code:02X} "
            f"<- 0x{source_code:02X} : "
            f"offset "
            f"{old_offset} -> {new_offset}, "
            f"{bitmap_size} bytes"
        )

    return new_glyphs, new_bitmaps


# ============================================================
# ФОРМАТИРОВАНИЕ BITMAPS
# ============================================================

def format_bitmaps(values):

    lines = []

    for i in range(
        0,
        len(values),
        12
    ):

        chunk = values[
            i:i + 12
        ]

        lines.append(
            "    "
            + ", ".join(
                f"0x{x:02X}"
                for x in chunk
            )
            + ","
        )

    return "\n".join(lines)


# ============================================================
# ФОРМАТИРОВАНИЕ GLYPHS
# ============================================================

def format_glyphs(glyphs):

    lines = []

    for glyph in glyphs:

        lines.append(
            "    {"
            + ", ".join(
                str(x)
                for x in glyph
            )
            + "},"
        )

    if lines:

        lines[-1] = lines[-1].rstrip(",")

    return "\n".join(lines)


# ============================================================
# ЗАМЕНА МАССИВА
# ============================================================

def replace_array(
    text,
    pattern,
    new_body
):

    result = re.sub(
        pattern,
        lambda m:
            m.group(1)
            + "\n"
            + new_body
            + "\n"
            + m.group(2),
        text,
        count=1,
        flags=re.DOTALL
    )

    if result == text:

        raise RuntimeError(
            "Не удалось заменить массив."
        )

    return result


# ============================================================
# ИЗМЕНЕНИЕ GFXfont FIRST/LAST
# ============================================================

def replace_font_range(
    text
):

    pattern = (
        r"(const\s+GFXfont\s+\w+"
        r"\s+PROGMEM\s*=\s*\{"
        r".*?"
        r"\(GFXglyph\s*\*\)\w+\s*,"
        r"\s*)"
        r"(0x[0-9A-Fa-f]+|\d+)"
        r"\s*,\s*"
        r"(0x[0-9A-Fa-f]+|\d+)"
        r"\s*,"
    )

    result = re.sub(
        pattern,
        lambda m:
            m.group(1)
            + f"0x{FIRST_CHAR:02X}, "
            + f"0x{LAST_CHAR:02X},",
        text,
        count=1,
        flags=re.DOTALL
    )

    if result == text:

        raise RuntimeError(
            "Не удалось изменить диапазон GFXfont."
        )

    return result


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def convert(
    input_file,
    output_file
):

    input_path = Path(
        input_file
    )

    output_path = Path(
        output_file
    )

    print()
    print(
        "Adafruit GFX Russian font converter"
    )
    print(
        "==================================="
    )
    print()

    print(
        f"Input : {input_path}"
    )

    print(
        f"Output: {output_path}"
    )

    print()

    # --------------------------------------------------------
    # Читаем исходный файл
    #
    # latin-1 позволяет читать любой байтовый файл без
    # ошибки UTF-8.
    # --------------------------------------------------------

    text = input_path.read_text(
        encoding="latin-1"
    )

    # --------------------------------------------------------
    # Bitmaps
    # --------------------------------------------------------

    (
        bitmap_match,
        bitmap_name,
        source_bitmaps
    ) = find_bitmaps(text)

    print(
        f"Bitmap array: {bitmap_name}"
    )

    print(
        f"Bitmap bytes: "
        f"{len(source_bitmaps)}"
    )

    # --------------------------------------------------------
    # Glyphs
    # --------------------------------------------------------

    (
        glyph_match,
        glyph_name,
        source_glyphs
    ) = find_glyphs(text)

    print(
        f"Glyph array : {glyph_name}"
    )

    print(
        f"Glyph count : "
        f"{len(source_glyphs)}"
    )

    source_first = 0x20

    source_last = (
        source_first
        + len(source_glyphs)
        - 1
    )

    print(
        f"Source range: "
        f"0x{source_first:02X} - "
        f"0x{source_last:02X}"
    )

    # --------------------------------------------------------
    # Проверяем исходный font
    # --------------------------------------------------------

    print()
    print(
        "Checking source glyphs..."
    )
    print()

    bad_glyphs = []

    for code in range(
        source_first,
        source_last + 1
    ):

        glyph = get_glyph(
            source_glyphs,
            source_first,
            code
        )

        offset = glyph[0]
        size = glyph_bitmap_size(
            glyph
        )

        end = offset + size

        if end > len(source_bitmaps):

            bad_glyphs.append(
                (
                    code,
                    offset,
                    size,
                    end,
                    len(source_bitmaps)
                )
            )

            print(
                f"WARNING: "
                f"0x{code:02X}: "
                f"offset={offset}, "
                f"size={size}, "
                f"end={end}, "
                f"bitmap size="
                f"{len(source_bitmaps)}"
            )

    if not bad_glyphs:

        print(
            "All source glyphs are valid."
        )

    # --------------------------------------------------------
    # Перестраиваем glyphs + Bitmaps
    # --------------------------------------------------------

    (
        new_glyphs,
        new_bitmaps
    ) = rebuild_bitmaps(
        source_glyphs,
        source_first,
        source_bitmaps
    )

    # --------------------------------------------------------
    # Форматируем массивы
    # --------------------------------------------------------

    new_bitmap_body = format_bitmaps(
        new_bitmaps
    )

    new_glyph_body = format_glyphs(
        new_glyphs
    )

    # --------------------------------------------------------
    # Заменяем Bitmaps[]
    # --------------------------------------------------------

    bitmap_pattern = (
        rf"(const\s+uint8_t\s+"
        rf"{re.escape(bitmap_name)}"
        rf"\s*\[\]\s*PROGMEM\s*=\s*\{{)"
        rf".*?"
        rf"(\}};)"
    )

    new_text = replace_array(
        text,
        bitmap_pattern,
        new_bitmap_body
    )

    # --------------------------------------------------------
    # Заменяем Glyphs[]
    # --------------------------------------------------------

    glyph_pattern = (
        rf"(const\s+GFXglyph\s+"
        rf"{re.escape(glyph_name)}"
        rf"\s*\[\]\s*PROGMEM\s*=\s*\{{)"
        rf".*?"
        rf"(\}};)"
    )

    new_text = replace_array(
        new_text,
        glyph_pattern,
        new_glyph_body
    )

    # --------------------------------------------------------
    # Устанавливаем first = 0x20
    # и last = 0xBF
    # --------------------------------------------------------

    new_text = replace_font_range(
        new_text
    )

    # --------------------------------------------------------
    # Сохраняем
    # --------------------------------------------------------

    output_path.write_text(
        new_text,
        encoding="latin-1"
    )

    # --------------------------------------------------------
    # Проверка результата
    # --------------------------------------------------------

    print()
    print(
        "==================================="
    )

    print(
        "RESULT"
    )

    print(
        "==================================="
    )

    print()

    print(
        f"Glyph range : "
        f"0x{FIRST_CHAR:02X} - "
        f"0x{LAST_CHAR:02X}"
    )

    print(
        f"Glyph count : "
        f"{len(new_glyphs)}"
    )

    print(
        f"Old Bitmaps : "
        f"{len(source_bitmaps)} bytes"
    )

    print(
        f"New Bitmaps : "
        f"{len(new_bitmaps)} bytes"
    )

    print(
        f"Saved       : "
        f"{len(source_bitmaps) - len(new_bitmaps)} bytes"
    )

    print()

    print(
        "ГОТОВО"
    )

    print()


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) < 2:

        print(
            "Использование:"
        )

        print()

        print(
            "  python gfx_font_rus_converter.py input.h"
        )

        print()

        print(
            "Или:"
        )

        print()

        print(
            "  python gfx_font_rus_converter.py "
            "input.h output.h"
        )

        return

    input_file = sys.argv[1]

    if len(sys.argv) >= 3:

        output_file = sys.argv[2]

    else:

        input_path = Path(
            input_file
        )

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
        print(
            "ОШИБКА:"
        )
        print(
            error
        )
        print()

        sys.exit(1)


if __name__ == "__main__":

    main()
