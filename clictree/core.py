from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Iterator, List, Optional, TypeVar, Union, \
    get_args, get_origin

from clictree.identifiers import PatientIdentifier, UNKNOWN_PATIENT, URI, \
    ResultReference, URIScope

# variables used in abstract base classes below
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

class Identity(Transformation[Any, Any]):
    """Let data through unaltered.

    All other transformation child classes are in clictree.transformations. This one
    is an exception as it is part of the default Link implementation below
    """

    def transform(self, input_data: Any) -> Any:
        return input_data


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

    def to_key(self, key_str: str) -> KeyType:
        """Create a Key instance of a type that can be used in .retrieve() for this
        Store
        """
        return self.key_type()(key_str)


class TransformedStore(Store[ResultReference, OutputType],
                       Generic[OutputType]):
    """A store that is a transformed view of another collection (store or collection)

    Warning
    -------
    This allows the creation of reference loops A->B->A that will cause the stack
    to overflow when you call retrieve()
    Don't create reference loops OK?
    """
    def __init__(self, data_source: Store[Any,InputType],
                 transformation: Transformation[InputType,OutputType]):
        self.data_source = data_source
        self.transformation = transformation

    def get_source_key(self, key: ResultReference):
        """Which key in source corresponds to the key asked for?

        By default, this just patches through the key value unaltered, meaning
        that asking for 'patient1' in this TransformedStore will yield a transformed
        'patient1' from the datasource
        """
        return self.data_source.to_key(key.value)


    def retrieve(self, key: ResultReference) -> OutputType:
        return self.transformation.transform(
            self.data_source.retrieve(self.get_source_key(key)))


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

    It does not contain data. Only references to data. The Context provides the
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

    def __init__(self, containers:Optional[Dict[str, Container]]=None):
        if not containers:
            containers = {}
        self.containers = containers

    def register_container(self, container:Container, name:str):
        if name in self.containers:
            raise ValueError(f'container "{name}" already exists')
        self.containers[name] = container

    def container_names(self) -> Dict[Container, str]:
        return {y:x for x,y in self.containers.items()}


    def get_uri(self, identifier) -> URI:
        """Get a URI to this identifier within domain

        Where in this domain is the data that this identifier is pointing to?
        """
        pass

    def get_data_item(self, uri: URI) -> DataItem:

        if uri.scope() > URIScope.CONTAINER:
            raise ValueError(f'Cannot use this URI "{uri}" as it it refers to a domain'
                             f' "{uri.domain_name}". I do not know whether I am that'
                             f' domain. Not assuming too much. Please remove the domain'
                             f'name part of URI')

        # resolve URI
        container = self.containers[uri.container_name]

         # find the identifier to use as key
        key = container.key_type()(uri.data_item_uid)
        return container.retrieve(key)


class Context:
    """Highest-level location in clic. Can contain multiple domains.

    Responsibilities
    ----------------
    * Holds credentials
    * Resolves URIs above domain level
    * Holds domain-boundary crossing links
    """
    def __init__(self, domains:Optional[Dict[str,Domain]]=None,
                 links:Optional[Dict[str,"Link"]]=None):
        if domains is None:
            domains = []
        if links is None:
            links = []
        self.domains = domains
        self.links = links

    def get_data_item(self, uri: URI) -> DataItem:
        """Get the DataItem indicated by a domain-level URI"""

        if uri.scope() > URIScope.DOMAIN:
            raise ValueError(f'Cannot use URI {uri} as it its scope is broader than'
                             f'DOMAIN. I can only get data items from within a context,'
                             f'not between contexts')

        domain = self.domains[uri.domain_name]
        # make sure uri only references container and uid
        container_lvl_uri = URI.from_string(str(uri))
        container_lvl_uri.domain_name = None
        return domain.get_data_item(container_lvl_uri)


class Link(ABC, Generic[InputType,OutputType]):
    """A transforming connection between two containers. Can cross a domain boundary.
    Translates Identifiers between domains. Is one-directional.
    A link A -> B means A can access a transformation of
    DataItems in B. InputType is the data coming from B, OutputType is the
    data being passed to A.

    A link reasons across domains so can only exist at the context level or higher.
    Link itself cannot collect data. It is only a tool used by context to know
    what to collect and how to transform.
    """

    def __init__(self, data_source_container: URI, context:Context,
                 transformation:Optional[Transformation]=None):
        """

        Parameters
        ----------
        data_source_container:
            A URI "//domain/container". The name of the data source
        context:
            linking whole context. here to enable Link to perform domain-level actions.
            This will be behind some kind of authorisation layer in the future
        transformation, optional:
            Transformation for any data requested through this link. Defaults to
            Identity, meaning data is let through unaltered
        """
        self.data_source_container = data_source_container
        self.context = context
        if transformation is None:
            transformation = Identity()
        self.transformation = transformation

    @abstractmethod
    def get_original_uri(self, reference: ResultReference) -> URI:
        """Given the reference used in A, what in B does this point to?
        Raises
        ------
        ValueError
            If no URI can be found for reference
        """
        # TODO: Think about inferring the datatype of the original reference. Is this
        # possible? It's important for keyfile management
        pass

    @abstractmethod
    def transform(self, input_data: InputType) -> OutputType:
        """Tranform the given input data into the given output.

        Raises
        ------
        TransformationError:
            If the transformation cannot be completed for any reason
        """
        self.transformation.transform(input_data)

    def get_data_item(self, reference: ResultReference) -> OutputType:
        """Obtain a transformed version of the referenced DataItem"""
        org_uri = self.get_original_uri(reference)
        return self.transform(
            self.context.get_data_item(org_uri))



class LinkedContainer(Store[ResultReference, OutputType]):
    """Represents a link to a container in a different domain. This is the only place
    within a domain that you can access DataItems from other domains. What you receive
    is always a transformation, never the original DataItem.
    """
    def __init__(self, link:Link[Any,OutputType]):
        self.link = link

    def retrieve(self, key: ResultReference) -> OutputType:
        return self.link.get_data_item(key)




