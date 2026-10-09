import pydicom

from abc import ABC, abstractmethod
from typing import Generic, Iterator, List, Optional, TypeVar, Union

from clictree.identifiers import PatientIdentifier, UNKNOWN_PATIENT, URI

# in clictree all studies are represented by pydicom datasets
Instance = pydicom.Dataset

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")
KeyType = TypeVar("KeyType")



class Transformation(ABC, Generic[InputType, OutputType]):
    """Change a data item somehow"""
    @abstractmethod
    def transform(self, input_data: InputType) -> OutputType:
        """Tranform the given input data into the given output.

        Raises
        ------
        TransformationError:
            If the transformation cannot be completed for any reason
        """
        pass

class Repository(ABC, Generic[KeyType, OutputType]):
    """A thing that can provide a specific dataitem by key"""
    @abstractmethod
    def retrieve(self, key: KeyType) -> OutputType:
        pass

class Source(ABC, Generic[OutputType]):
    """A thing that you can retrieve data mapping from without a key"""

    @abstractmethod
    def __iter__(self) -> Iterator[OutputType]:
        pass

class Store(ABC, Generic[InputType, KeyType]):

    @abstractmethod
    def write(self, data_item: InputType) -> KeyType:
        pass


class DataItem(ABC, Generic[OutputType]):
    """The thing that is being moved around and transformed in clictree

    Always associated with a patient
    """

    def __init__(self, patient:Optional[PatientIdentifier]):
        if patient is None:
            patient = UNKNOWN_PATIENT
        self.patient = patient

    @abstractmethod
    def data(self) -> OutputType:
        pass


class Collection:
    """A collection of data item references collected for a certain purpose"""

    def __init__(self, items: Optional[List[URI]] = None, cmo:str=""):
        """
        Parameters
        ----------
        items:
            All data items in this collection. Represented by URI
        cmo
        """
        if items is None:
            items = []
        self.items = items
        self.cmo = cmo


class KeyFile(ABC):
    """A store and generator for orginal -> pseudonym mappings

    Main method is

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

    @abstractmethod
    def retrieve_pseudonym(self, key:KeyType) -> KeyType:
        """Find the pseudonym for this key

        Raises
        ------
        KeyError
            If no pseudonym can be found
        """
        pass

    @abstractmethod
    def retrieve_original(self, pseudonym: KeyType) -> KeyType:
        """Find the original key for this pseudonym

        Raises
        ------
        KeyError
            If no original key can be found
        """
        pass

    def obtain_pseudonym(self, key:KeyType) -> KeyType:
        """Find pseudonym for this key, generate if it cannot be found

        Raises
        ------
        KeyError
            If pseudonym could not be obtained
        """
        try:
            return self.retrieve_pseudonym(key)
        except KeyError:
            try:
                return self.generate_pseudonym(key)
            except NotImplementedError as e:
                raise KeyError(f"Cannot obtain a pseudonym for {key}") from e


    def generate_pseudonym(self, key:KeyType) -> KeyType:
        """Create a new pseudonym for the given key"""

        raise NotImplementedError("No method to generate pseudonyms!")



class Domain:
    """A pseudonymization domain. All collections in a domain share the measures they
    put in place to protect patient confidentiality. This includes pseudonymization.

    You cannot directly access anything across a domain boundary. The only way to
    interface with anything across a domain boundary is through a Link.
    """

    def __init__(self, key_file: KeyFile):
        self.key_file = key_file

class Link:
    """Connects Collection A with Collection or Source B. Is one-directional. A link
    A -> B means A can access DataItems in B. Access is never direct, but always
    through a transformation.
    """

    def __init__(self, collection_a: Collection, container_b:Container):
        pass
