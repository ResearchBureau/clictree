import pydicom

from abc import ABC, abstractmethod
from typing import ClassVar, Dict, Generic, Iterable, Iterator, List, Optional, TypeVar, \
    Union, get_args, get_origin

from clictree.identifiers import Identifier, PatientIdentifier, UNKNOWN_PATIENT, URI

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

class Store(ABC, Generic[KeyType, OutputType]):
    """A thing that can provide a specific dataitem by key"""

    @abstractmethod
    def retrieve(self, key: KeyType) -> OutputType:
        pass

    @classmethod
    def key_type(cls):   #possible dark magic.
        for base in getattr(cls, "__orig_bases__", ()):
            if get_origin(base) is Store:
                return get_args(base)[0]
        raise TypeError(f"{cls.__name__} does not bind KeyType")


class Source(ABC, Generic[OutputType]):
    """A thing that you can retrieve data mapping from without a key"""

    @abstractmethod
    def __iter__(self) -> Iterator[OutputType]:
        pass

class Deposit(ABC, Generic[InputType, KeyType]):
    """Something you can write a data item to, and get a key back"""
    @abstractmethod
    def write(self, data_item: InputType) -> KeyType:
        pass


class DataItem(ABC, Generic[OutputType]):
    """The thing that is being moved around and transformed in clictree

    Always associated with a patient
    """

    def __init__(self,  data:OutputType, patient:Optional[PatientIdentifier]=None):
        self.data = data
        if patient is None:
            patient = UNKNOWN_PATIENT
        self.patient = patient


class Collection:
    """A collection of data item references collected for a certain purpose.

    I does not contain data. Only references to data. The Context provides the
    actual data
    """

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

Container = Union[Collection, Store]

class Domain:
    """A pseudonymization domain. All collections in a domain share the measures they
    put in place to protect patient confidentiality. This includes pseudonymization.

    Responsibilities and properties
    -------------------------------
    * Domain controls all Identifiers used within it. It knows about all identifiers,
    can generate new ones if needed.
    * Domain knows about all containers inside it and names them
    * Domain resolves UID chains into executable form to be able to call the right
    method of the right containers in order to provide DataItems.
    * How to actually obtain DataItems given an Identifier is NOT part of domain, but
    left to the container

    You cannot directly access anything across a domain boundary. The only way to
    interface with anything across a domain boundary is through a LinkedContainer.
    """

    def __init__(self, containers:Optional[Dict[str, Container]]=None,
                 transformation_map:Optional[Dict[str, str]]=None):
        if not containers:
            containers = {}
        self.containers = containers
        if not transformation_map:
            transformation_map = {}
        self.transformation_map = transformation_map

    def register_container(self, container:Container, name:str):
        if name in self.containers:
            raise ValueError(f'container "{name}" already exists')
        self.containers[name] = container

    def container_names(self) -> Dict[Container, str]:
        return {y:x for x,y in self.containers.items()}


    def register_transformation(self,  output_uri:URI,
                                input_uri:URI
                               ):
        """Tell domain that you obtain output_uri by feeding in input_uri"""
        self.transformation_map[output_uri] = input_uri


    def get_uri(self, identifier) -> URI:
        """Get a URI to this identifier within domain

        Where is in this domain is the data that this identifier is pointing to?
        """
        pass

    def get_data_item(self, uri: URI) -> DataItem:

        # resolve URI
        container = self.containers[uri.container_name]

        if source_url:= self.transformation_map.get(uri):
            # This is a transformer. We need to obtain other data before being able
            # to return data for this
            # TODO tighten type checking. container might not be a transformation
            #
            required_input = self.get_data_item(source_url)
            return container.transform(required_input)


        else:
            # find the identifier to use as key
            key = container.key_type()(uri.data_item_uid)
            return container.retrieve(key)


class TransformationMap:
    """"""

class Context:
    """Highest-level location in clic. Can contain multiple domains. Responsibilities
    are holding credentials, resolving URIs and guiding data item transfer.
    """
    def __init__(self, domains=Optional[List[Domain]]):
        self.domains = domains



class Link:
    """Connects Collection A with Collection or Source B. Is one-directional. A link
    A -> B means A can access DataItems in B. Access is never direct, but always
    through a transformation.
    """

    def __init__(self, collection_a: Collection, container_b:Container):
        pass
