'''Python objects for storing config info'''
import json
import os
from types import SimpleNamespace, MappingProxyType

with open(os.path.join(os.path.dirname(__file__), "languages.json"), 'rb') as lang:
    LANGUAGES: MappingProxyType = MappingProxyType(json.loads(lang.read()))

with open(os.path.join(os.path.dirname(__file__), "config.json"), "rb") as config:
    FLAGS: SimpleNamespace = SimpleNamespace(**{flag: default for flag, default in json.loads(config.read())['flags'].items()})