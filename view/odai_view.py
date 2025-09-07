import discord
import os

def make_file(filename):
    path = os.path.join("img", filename)
    return discord.File(path)
