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
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Dict, Generic, Optional, Type, get_args, get_origin

from clictree.core import KeyType, Store
from clictree.exceptions import KeyFileError
from clictree.identifiers import AccessionNumber, Identifier, PatientIdentifier


class Backend(ABC):
    """A thing that holds key-key pairs"""

    @abstractmethod
    def retrieve_value(self, key: Identifier) -> Identifier:
        """Find the value associated with this key

        Raises
        ------
        KeyError
            If key cannot be found
        """
        pass

    @abstractmethod
    def retrieve_key(self, value: Identifier) -> Identifier:
        """Find the key associated with this value

        Raises
        ------
        KeyError
            If key cannot be found
        """
        pass

    @abstractmethod
    def insert(self, key: Identifier, value: Identifier):
        """Insert the given pair into this backend. Overwrite if exists"""
        pass


class KeyMap(ABC, Generic[KeyType]):
    """A store and generator for single-type key -> pseudo_key pairs

    Child classes must implement retrieve_pseudonym() and retrieve_original()
    Child classes may implement generate_pseudonym()

    Comments
    --------
    Considered giving keyfile a dict-like interface but decided against it. Opted
    instead for explicit method calls for two main reasons.
    1) There is no natural dict-like mapping for the distinction between retrieve
    (get it if its there) and obtain (generate if you can't retrieve).
    2) dict-like interface indicates quick, direct-memory access. For several KeyFile
    implementations, obtaining might involve server querying and not be as quick
    as the interface suggests.
    """

    def __init__(self, backend: Backend):
        self.backend=backend

    @classmethod
    def key_type(cls):  # possible dark magic.
        for base in getattr(cls, "__orig_bases__", ()):
            if get_origin(base) is KeyMap:
                return get_args(base)[0]
        raise TypeError(f"{cls.__name__} does not bind KeyType")

    def retrieve_pseudonym(self, key:KeyType) -> KeyType:
        """Find the pseudonym for this key

        Raises
        ------
        KeyError
            If no pseudonym can be found
        """
        return self.backend.retrieve_value(key)


    def retrieve_original(self, pseudonym: KeyType) -> KeyType:
        """Find the original key for this pseudonym

        Raises
        ------
        KeyError
            If no original key can be found
        """
        return self.backend.retrieve_key(pseudonym)

    def obtain_pseudonym(self, key:KeyType) -> KeyType:
        """Find pseudonym for this key, generate if it cannot be found.
        Generated pseudonyms are stored so this function can modify backend

        Raises
        ------
        KeyError
            If pseudonym could not be obtained
        """
        try:
            return self.retrieve_pseudonym(key)
        except KeyError:
            try:
                self.backend.insert(self.generate_pseudonym(key),key)
                return self.retrieve_pseudonym(key)
            except NotImplementedError as e:
                raise KeyError(f"Cannot obtain a pseudonym for {key}") from e


    def generate_pseudonym(self, key:KeyType) -> KeyType:
        """Create a new pseudonym for the given key"""

        raise NotImplementedError("No method to generate pseudonyms!")


class KeyFile:
    """Holds key map for one or more key types

    Can offer a shared backend.

    Notes
    -----
    Scoped to handle only Identifier instances to make a clear distinction between a
    keyfile (holds key-pseudonym pairs) and a database (holds key-anydata). If an
    implementor wants to 'stash data' they need to use a database, not a key file
    """
    def __init__(self, key_maps:Optional[Dict[Type[Identifier],KeyMap]]=None):
        if key_maps is None:
            key_maps = {}
        self.key_maps = key_maps

    def add_map(self,key_map:KeyMap):
        self.key_maps[key_map.key_type()] = key_map

    def get_map(self, key: Identifier) -> KeyMap:
        """Get the KeyMap matching this key's Type

        Raises
        ------
        KeyFileError
            If no KeyMap can be found
        """
        try:
            return self.key_maps[(type(key))]
        except KeyError as e:
            raise KeyFileError(f'Cannot find KeyMap for {key} '
                               f'(type "{type(key)}")') from e


    def retrieve_pseudonym(self, key: Identifier) -> Identifier:
        """Find the pseudonym for this key

        Raises
        ------
        KeyFileError
            If no pseudonym can be retrieved
        """
        key_map = self.get_map(key)
        try:
            return key_map.retrieve_pseudonym(key)
        except KeyError as e:
            raise KeyFileError(f'Cannot retrieve pseudonym for {key}') from e


    def retrieve_original(self, pseudonym: Identifier) -> Identifier:
        """Find the original key for this pseudonym

        Raises
        ------
        KeyError
            If no original key can be found
        """
        key_map = self.get_map(pseudonym)
        try:
            return key_map.retrieve_original(pseudonym)
        except KeyError as e:
            raise KeyFileError(f'Cannot retrieve original for {pseudonym}') from e

    def obtain_pseudonym(self, key: Identifier) -> Identifier:
        """Find pseudonym for this key, generate if it cannot be found

        Raises
        ------
        KeyError
            If pseudonym could not be obtained
        """
        key_map = self.get_map(key)
        try:
            return key_map.retrieve_pseudonym(key)
        except KeyError:
            try:
                return key_map.generate_pseudonym(key)
            except NotImplementedError as e:
                raise KeyError(f"Cannot obtain a pseudonym for {key}") from e



class MemoryOnlyBackend(Backend):
    """Saves everything in memory only"""

    def __init__(self):
        self.mapping = defaultdict(dict)
        self.reversed_mapping = defaultdict(dict)

    def retrieve_key(self, value: Identifier) -> Identifier:
        # not going for any optimization here
        return self.reversed_mapping[type(value)][value]

    def insert(self, key: Identifier, value: Identifier):
        self.mapping[type(key)][key] = value
        self.reversed_mapping[type(value)][value] = key

    def retrieve_value(self, key: Identifier) -> Identifier:
        return self.mapping[type(key)][key]


class PatientIdentifierMap(KeyMap[PatientIdentifier]):
    pass

class AccessionNumberMap(KeyMap[AccessionNumber]):
    pass