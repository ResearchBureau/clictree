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

from clictree.core import KeyType
from clictree.identifiers import AccessionNumber, Identifier, PatientIdentifier


class Backend(ABC):
    """A thing that holds key-key pairs for two columns A and B. Can handle multiple
    Key types

    You can request a key from either column to retrieve its counterpart
    """


    @abstractmethod
    def retrieve_from_column_b(self, key_a: Identifier) -> Identifier:
        """Find the column B value for given column A key

        Raises
        ------
        KeyError
            If key cannot be found
        """
        pass

    @abstractmethod
    def retrieve_from_column_a(self, key_b: Identifier) -> Identifier:
        """Find the column A value for given column B key

        Raises
        ------
        KeyError
            If key cannot be found
        """
        pass

    @abstractmethod
    def insert(self, key_a: Identifier, key_b: Identifier):
        """Insert the given keys into column A and column B. Overwrite if exists.
        """
        pass



class KeyMap(ABC, Generic[KeyType]):
    """A store and generator for single-type key -> counterpart key pairs between
    two specific domains.

    Responsibilities
    ----------------
    * Hold on to the two domains that this keymap maps between
    * Perform the logic required for allowing key-key lookup from either domain
    * Be able to read, generate and write keys and their counterparts from either
      domain to the other
    * Generating and saving counterpart keys, if configured. It is fine to not
      generate and raise exception instead, but if any generating is done, KeyMap
      should define and perform it.


    Comments
    --------
    Considered giving keyfile a dict-like interface but decided against it. Opted
    instead for explicit method calls for two main reasons.
    1) There is no natural dict-like mapping for the distinction between retrieve
    (get it, error if you can't) and obtain (get it, generate if you can't).
    2) dict-like interface indicates quick, direct-memory access. For several KeyFile
    implementations, obtaining might involve server querying and not be as quick
    as a dict interface suggests.

    """

    def __init__(self, backend: Backend, domain_a:str, domain_b:str):
        self.backend=backend
        self.domain_a = domain_a
        self.domain_b = domain_b

    @classmethod
    def key_type(cls):  # possible dark magic.
        for base in getattr(cls, "__orig_bases__", ()):
            if get_origin(base) is KeyMap:
                return get_args(base)[0]
        raise TypeError(f"{cls.__name__} does not bind KeyType")

    def retrieve_counterpart(self, domain_name: str, key:KeyType) -> KeyType:
        """Find the counterpart for this key from domain.

        Raises
        ------
        ValueError
            If domain cannot be found
        KeyError
            If no pseudonym can be found
        """
        if domain_name == self.domain_a:
            return self.backend.retrieve_from_column_b(key_a=key)
        elif domain_name == self.domain_b:
            return self.backend.retrieve_from_column_a(key_b=key)
        else:
            raise(self.get_domain_name_error(domain_name))


    def obtain_counterpart(self, domain_name:str, key:KeyType) -> KeyType:
        """Find counterpart for this key from domain, generate if it cannot be found.
        Generated pseudonyms should be stored. This function could modify backend.

        Raises
        ------
        ValueError
            If domain cannot be found
        KeyError
            If pseudonym could not be found or generated
        """
        try:
            return self.retrieve_counterpart(domain_name, key)
        except KeyError:
            # could not find a saved counterpart. Generate, save to backend and return
            counterpart = self.generate_counterpart(domain_name, key)
            self.insert_counterpart(domain_name=domain_name,
                                    key=key, counterpart=counterpart)
            return self.retrieve_counterpart(domain_name, key)


    def generate_counterpart(self, domain_name, key:KeyType) -> KeyType:
        """Create a counterpart for the given key in domain.

        Note
        ----
        The call references the domain that the key is *currently in*.
        Not the domain that the counterpart will be generated in.

        Raises
        ------
        ValueError
            If domain name does not exist
        NotImplementedError
            If no generation is possible
        """
        if domain_name == self.domain_a:
            return self.generate_a_to_b(key)
        elif domain_name == self.domain_b:
            return self.generate_b_to_a(key)
        else:
            raise(self.get_domain_name_error(domain_name))

    def insert_counterpart(self, domain_name, key, counterpart):
        """Write the given key for domain and its counterpart to backend"""
        if domain_name == self.domain_a:
            self.backend.insert(key_a=key, key_b=counterpart)
        elif domain_name == self.domain_b:
            self.backend.insert(key_a=counterpart, key_b=key)
        else:
            raise(self.get_domain_name_error(domain_name))


    def get_domain_name_error(self, domain_name: str):
        return ValueError(f'Unknown domain "{domain_name}".'
                          f' Options were "{(self.domain_a, self.domain_b)}"')

    def generate_a_to_b(self, key: KeyType) -> KeyType:
        """Given a key in domain A, generate a counterpart in domain B.
        """

        raise NotImplementedError("No method to generate keys defined from"
                                  f" '{self.domain_a}' to '{self.domain_b}'")

    def generate_b_to_a(self, key: KeyType) -> KeyType:
        """Given a key in domain B, generate a counterpart in domain A.
        """

        raise NotImplementedError("No method to generate keys defined from"
                                  f" '{self.domain_b}' to '{self.domain_a}'")



class KeyFile:
    """Holds key map for one or more key types

    Can offer a shared backend.

    Notes
    -----
    Scoped to handle only Identifier instances to make a clear distinction between a
    keyfile (holds key-pseudonym pairs) and a database (holds key-anydata). If an
    implementor wants to 'stash data' they need to use a database, not a key file.
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
        KeyError
            If no KeyMap can be found
        """
        try:
            return self.key_maps[(type(key))]
        except KeyError as e:
            raise KeyError(f'Cannot find KeyMap for {key} '
                           f'(type "{type(key)}")') from e


    def retrieve_counterpart(self, domain_name: str, key: Identifier) -> Identifier:
        """Find the counterpart for this key from domain

        Raises
        ------
        ValueError
            If domain cannot be found
        KeyError
            If no pseudonym can be retrieved
        """
        key_map = self.get_map(key)
        return key_map.retrieve_counterpart(domain_name, key)


    def obtain_pseudonym(self, domain_name:str, key: Identifier) -> Identifier:
        """Find the counterpart for this key from domain. Generate if not found.

        Raises
        ------
        ValueError
            If domain cannot be found
        KeyError
            If no pseudonym can be retrieved
        """
        key_map = self.get_map(key)
        return key_map.obtain_counterpart(domain_name, key)


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


class PatientIdentifierMap(KeyMap[PatientIdentifier]):
    pass

class AccessionNumberMap(KeyMap[AccessionNumber]):
    pass