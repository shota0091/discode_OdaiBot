import mysql.connector
import os
import random
from dotenv import load_dotenv
from entity.image_file import ImageFile
load_dotenv() 
conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)

def get_unsent_image():
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, sent FROM image_files WHERE sent = 0")
    results = cursor.fetchall()
    if not results:
        return None
    selected = random.choice(results)
    return ImageFile(*selected)

def mark_image_sent(image: ImageFile):
    cursor = conn.cursor()
    cursor.execute("UPDATE image_files SET sent = 1 WHERE id = %s", (image.id,))
    conn.commit()
