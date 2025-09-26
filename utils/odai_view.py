from PIL import Image, ImageDraw, ImageFont
import os

def save_odai_image_to_file(text: str, path: str, font_name: str = "NotoSansJP-Bold.ttf"):
    # 出力画像サイズ
    width, height = 1280, 720

    # 背景画像（白）
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # フォント読み込み
    font_path = os.path.join("fonts", font_name)
    font_size = 60
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        raise ValueError(f"フォントの読み込みに失敗しました: {font_path}\n{e}")

    # テキスト中央寄せ位置の計算
    text_width, text_height = draw.textsize(text, font=font)
    position = ((width - text_width) // 2, (height - text_height) // 2)

    # 描画（シャドウなどは未使用）
    draw.text(position, text, font=font, fill=(0, 0, 0))

    # ディレクトリ作成
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # 保存
    img.save(path)
    return path
