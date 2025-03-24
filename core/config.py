'''Python objects for storing config info'''
import json
import os

with open(os.path.join(os.path.dirname(__file__), "languages.json"), 'rb') as lang:
    LANGUAGES: dict = json.loads(lang.read())

with open(os.path.join(os.path.dirname(__file__), "config.json"), "rb") as config:
    FLAGS: dict = json.loads(config.read())['flags']