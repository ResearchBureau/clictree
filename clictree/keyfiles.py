"""Classes and methods for handling key-pseudonym pairs


Notes
-----
Why so complicated? - Why have a KeyFile containing KeyMaps referencing Backend?
Why split things up so much?

Because 'A keyfile' has the following requirements:
1) The types of keys that are supported can vary and should be explicit (see below)
2) The backend should be switchable.
3) The 'KeyFile' class should have a clean, universal interface.

KeyMap makes the types of keys that are supported explicit (1) This is important
because you want to be able to explicitly reference the types of keys that are
required for a transformation. If you have a 'pseudonymize' Transformation for
example, it is important to know in advance whether you need to define an
accession_number pseudonym generator or not. If you do not explicitly define this,
an implementor would have to scour the transformation code before switching to a
different keyfile backend for example.

Backend is separate for easy switching

KeyFile presents a clean interface: Once you have defined and instantiated a KeyFile
object you can just feed it Identifiers, and it will work as expected.
"""
from collections import defaultdict
from typing import Dict, Type

from clictree.core import Backend, KeyMap
from clictree.identifiers import AccessionNumber, DICOMStudyIdentifier, Identifier, \
    PatientIdentifier


class MemoryOnlyBackend(Backend):
    """Saves everything in memory only

    Saves pairs per column and per KeyType
    """

    def __init__(self):
        self.mapping = defaultdict(dict)  # a to b
        self.reversed_mapping = defaultdict(dict)  # b to a

    def retrieve_from_column_b(self, key_a: Identifier) -> Identifier:
        # not going for any optimisation here
        return self.mapping[type(key_a)][key_a]

    def retrieve_from_column_a(self, key_b: Identifier) -> Identifier:

        return self.reversed_mapping[type(key_b)][key_b]

    def insert(self, key_a: Identifier, key_b: Identifier):

        self.mapping[type(key_a)][key_a] = key_b
        self.reversed_mapping[type(key_b)][key_b] = key_a


    def insert_batch(self, values:Dict[str,str], key_type=Type[Identifier]):
        """Insert all values {val_a:val_b, ...} as type key_type
        Convenience function for seeding values
        """
        for val_a, val_b in values.items():
            self.insert(key_a=key_type(value=val_a),key_b=key_type(value=val_b))


class StudyIdentifierMap(KeyMap[DICOMStudyIdentifier]):
    pass

class PatientIdentifierMap(KeyMap[PatientIdentifier]):
    pass

class AccessionNumberMap(KeyMap[AccessionNumber]):
    pass