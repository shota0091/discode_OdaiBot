# utils/font_helper.py
import os

def get_available_fonts():
    font_dir = "font"
    font_files = []
    for filename in os.listdir(font_dir):
        if filename.lower().endswith(('.ttf', '.ttc', '.otf')):
            font_files.append(filename)
    return font_files
