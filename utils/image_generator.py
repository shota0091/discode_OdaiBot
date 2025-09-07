import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from uuid import uuid4
from io import BytesIO

IMG_WIDTH = 1152
IMG_HEIGHT = 648
JP_FONT_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"

def wrap_text(draw, text, font, max_width):
    lines = []
    line = ""
    for ch in text:
        test_line = line + ch
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return "\n".join(lines)

from PIL import Image, ImageDraw, ImageFont
from uuid import uuid4

def generate_odai_image(template_path, text, font_path, text_color, font_size, shadow):
    # テンプレート画像を開く
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # フォントを読み込む
    font = ImageFont.truetype(font_path, font_size)

    # 影付き文字描画（少しずらして黒で描画）
    if shadow:
        draw.text((12, 12), text, font=font, fill="black")

    # 通常の文字描画（上に重ねる）
    draw.text((10, 10), text, font=font, fill=text_color)

    # 出力ファイルパスを生成
    output_path = f"generated_odai/{uuid4()}.png"
    img.save(output_path)

    return output_path


def generate_image(template_path, text, font_path, text_color, font_size, shadow):
    # テンプレート画像を読み込み
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    # 影つきテキスト（黒をずらして描画）
    if shadow:
        draw.text((12, 12), text, font=font, fill="black")
    draw.text((10, 10), text, font=font, fill=text_color)

    # 出力パス作成
    output_path = f"generated_odai/{uuid4()}.png"
    img.save(output_path)
    return output_path

def generate_blank_image_with_text(text, font_path, text_color, font_size, shadow):
    img = Image.new("RGBA", (1152, 648), "white")  # 白背景
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    if shadow:
        draw.text((12, 12), text, font=font, fill="black")
    draw.text((10, 10), text, font=font, fill=text_color)

    output_path = f"generated_odai/{uuid4()}.png"
    img.save(output_path)
    return output_path

def generate_blank_image_with_text(text, font_path, text_color, font_size, shadow):
    # 白背景のキャンバスを生成（HDサイズ）
    img = Image.new("RGBA", (1152, 648), "white")
    draw = ImageDraw.Draw(img)

    # フォント設定
    font = ImageFont.truetype(font_path, font_size)

    # テキストの描画位置（固定値）
    x, y = 10, 10

    # 影を描画する場合
    if shadow:
        draw.text((x + 2, y + 2), text, font=font, fill="black")  # 影の色は黒

    # 本体のテキスト描画
    draw.text((x, y), text, font=font, fill=text_color)

    # 出力ファイルパス
    output_path = f"generated_odai/{uuid4()}.png"
    img.save(output_path)

    return output_path