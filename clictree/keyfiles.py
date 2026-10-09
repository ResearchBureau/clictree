"""Common keyfile implementations"""
from typing import Dict

from clictree.core import KeyFile


class DictKeyFile(KeyFile):
    """A keyfile that is a dictionary internally"""

    def __init__(self, mapping: Dict):
        self.mapping = mapping

    def retrieve_pseudonym(self, key):
        return self.mapping[key]

    def retrieve_original(self, pseudonym):
        for key,value in self.mapping.items():
            if value == pseudonym:
                return key

        raise KeyError(f'Value "{pseudonym}" not found')


