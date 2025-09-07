import os
from uuid import uuid4
from datetime import datetime

def save_uploaded_image(guild_id: int, original_filename: str, binary_data: bytes):
    today = datetime.now().strftime("%Y-%m")
    upload_dir = os.path.join("uploads", today)
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(original_filename)[-1]
    unique_filename = f"{guild_id}_{uuid4().hex}{ext}"
    save_path = os.path.join(upload_dir, unique_filename)

    with open(save_path, "wb") as f:
        f.write(binary_data)

    return save_path, ext.replace('.', ''), len(binary_data)  # パス, 拡張子, サイズ（バイト）

def save_template_image(guild_id: int, original_filename: str, binary_data: bytes):
    from datetime import datetime
    from uuid import uuid4

    today = datetime.now().strftime("%Y-%m")
    save_dir = os.path.join("templates", today)
    os.makedirs(save_dir, exist_ok=True)

    ext = os.path.splitext(original_filename)[-1]
    unique_filename = f"{guild_id}_{uuid4().hex}{ext}"
    save_path = os.path.join(save_dir, unique_filename)

    with open(save_path, "wb") as f:
        f.write(binary_data)

    return save_path, ext.replace('.', ''), len(binary_data)