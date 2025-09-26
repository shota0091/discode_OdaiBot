import os
from PIL import Image, ImageDraw, ImageFont
from uuid import uuid4
import textwrap

IMG_WIDTH = 1152
IMG_HEIGHT = 648

def wrap_text_multiline(text, font, draw, max_width):
    lines = []
    line = ""
    for word in text:
        test_line = line + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def generate_odai_image_with_title(template_path: str, title: str, text: str,
                                   font_path: str, text_color: str, font_size: int,
                                   shadow: bool) -> str:
    # 背景テンプレート読み込み
    img = Image.open(template_path).convert("RGBA")
    img = img.resize((IMG_WIDTH, IMG_HEIGHT))

    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    # === タイトル描画 ===
    title_font = ImageFont.truetype(font_path, int(font_size * 0.6))
    title_w, title_h = draw.textbbox((0, 0), title, font=title_font)[2:]
    title_x = (IMG_WIDTH - title_w) // 2
    title_y = 60
    if shadow:
        draw.text((title_x + 2, title_y + 2), title, font=title_font, fill="black")
    draw.text((title_x, title_y), title, font=title_font, fill=text_color)

    # === 本文描画（中央揃え、複数行） ===
    lines = wrap_text_multiline(text, font, draw, IMG_WIDTH - 100)
    total_text_height = sum([draw.textbbox((0, 0), line, font=font)[3] for line in lines]) + (len(lines) - 1) * 10

    y = (IMG_HEIGHT - total_text_height) // 2 + 80  # タイトルの下の余白
    for line in lines:
        w, h = draw.textbbox((0, 0), line, font=font)[2:]
        x = (IMG_WIDTH - w) // 2
        if shadow:
            draw.text((x + 2, y + 2), line, font=font, fill="black")
        draw.text((x, y), line, font=font, fill=text_color)
        y += h + 10  # 行間

    # === 保存パス ===
    output_path = f"generated_odai/{uuid4()}.png"
    img.save(output_path)
    return output_path