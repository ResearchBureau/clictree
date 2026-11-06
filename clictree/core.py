from abc import ABC, abstractmethod
from typing import Any, Dict, FrozenSet, Generic, Iterator, List, Optional, Type, \
    TypeVar, Union, get_args, get_origin

from clictree.identifiers import Identifier, PatientIdentifier, UNKNOWN_PATIENT, URI, \
    ResultReference, URIScope

# variables used in abstract base classes below
InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")
KeyType = TypeVar("KeyType", bound=Identifier)


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
    """A thing that can provide a specific dataitem by key

    Responsibilities
    ----------------
    * Know how to retrieve its output data
    * Accepts its given key type
    * Be able to convert any string to its given key type

    You can use either the classes KeyType (always an Identifier subclass)
    or string to request data from a store. The idea is that string is quick and
    slightly sloppy, using an Identifier instance is more work (requires initialising
    the object, knowing which type to use) but unambiguous.

    For example, when requesting a study from a VNA store, you could use a
    retrieve('12345'). The store then has to guess what kind of key this is. It
    might guess it's an accession_number. As long as you work with accession numbers
    things work quick and easy. In case you actually want to use a StudyInstanceUID
    though, you could use retrieve(SUID('12345')) to make and unambiguous call.
    """

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
        item = container.retrieve(key)
        return item


class Context:
    """Highest-level location in clic. Holds domains and the Interfaces between them

    Responsibilities
    ----------------
    * Holds credentials
    * Resolves URIs above domain level
    * Links a unique name to all its domains
    * Manages all interfaces (connections between domains)
    """
    def __init__(self, domains:Dict[str,Domain]=None,
                 interfaces:Dict[FrozenSet[str],"Interface"]=None):
        """

        Parameters
        ----------
        domains:
            All domains part of this context, named
        interfaces:
            All interfaces between any of the domains. Key for each interface is
            a FrozenSet so {a,b} and {b,a} lead to the same interface
        """

        if domains is None:
            domains = {}
        if interfaces is None:
            interfaces = {}
        self.domains = domains
        self.interfaces = interfaces

    def add_interface(self, interface:"Interface"):
        self.interfaces[
            frozenset((interface.domain_a, interface.domain_b))] = interface

    def get_interface(self, domain_a:str, domain_b:str):
        return self.interfaces[frozenset((domain_a, domain_b))]

    def get_container(self, uri: URI) -> Container:
        """Get the Container object referenced by URI

        Raises
        ------
        ValueError
            If no container can be found
        """
        # todo: more type and format checking? For now just go with this.
        return self.domains[uri.domain_name].containers[uri.container_name]


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


class Link(Generic[InputType,OutputType]):
    """A transforming connection between two containers. Can cross a domain boundary.
    Translates Identifiers between domains. Is one-directional.
    A link A -> B means A can access a transformation of
    DataItems in B. InputType is the data coming from B, OutputType is the
    data being passed to A.

    A link reasons across domains so can only exist at the context level or higher.
    Link itself cannot collect data. It is only a tool used by context to know
    what to collect and how to transform.
    """

    def __init__(self, data_source_container: URI, destination_domain: str,
                 context:Context,
                 transformation:Optional[Transformation]=None):
        """

        Parameters
        ----------
        data_source_container:
            A URI "//domain/container". The name of the data source
        destination_domain: str
            Requests come from there, data is sent to there.
        context:
            linking whole context. here to enable Link to perform domain-level actions.
            This will be behind some kind of authorisation layer in the future
        transformation, optional:
            Transformation for any data requested through this link. Defaults to
            Identity, meaning data is let through unaltered
        """
        self.data_source_container = data_source_container
        self.destination_domain = destination_domain
        self.context = context
        if transformation is None:
            transformation = Identity()
        self.transformation = transformation

    @property
    def data_source_domain(self):
        return self.data_source_container.domain_name

    def get_original_key_type(self):
        return self.context.get_container(self.data_source_container).key_type()

    def get_original_uri(self, identifier: Identifier) -> URI:
        """Given an identifier pseudonym used in A (linked, target domain),
        what in B (source domain) does this point to?

        Parameters
        ----------
        identifier:
            Identifier coming from linkedContainer. The pseudonym under
            which a dataItem from another domain is known.

        Returns
        -------
        URI:
            The context-level path to the original dataItem

        Raises
        ------
        ValueError
            If no URI can be found for identifier
        """

        # Get Interface that this link is part of
        interface = self.context.get_interface(
            self.data_source_domain, self.destination_domain)

        # Try to translate the identifier to the data source domain
        translated_id = interface.retrieve_counterpart(
            domain_name=self.destination_domain, key=identifier)

        return URI(domain_name=self.data_source_domain,
                   container_name=self.data_source_container.container_name,
                   data_item_uid=translated_id.value)


    def transform(self, input_data: InputType) -> OutputType:
        """Tranform the given input data into the given output.

        Raises
        ------
        TransformationError:
            If the transformation cannot be completed for any reason
        """
        return self.transformation.transform(input_data)

    def get_data_item(self, identifier: Identifier) -> OutputType:
        """Obtain a transformed version of the referenced DataItem"""
        org_uri = self.get_original_uri(identifier)
        return self.transform(
            self.context.get_data_item(org_uri))


class LinkedContainer(Store[ResultReference, DataItem]):
    """Represents a link to a container in a different domain. This is the only place
    within a domain that you can access DataItems from other domains. Requires a Link
    instance to work. It can be seen as the in-domain representation of a context
    (higher than domain)-level Link.  What you receive is always a transformation,
    never the original DataItem.

    Responsibilities
    * Provide in-domain access to a Link instance
    * Cast any incoming ResultReference to the right key type


    """
    def __init__(self, link:Link[Any,DataItem]):
        self.link = link

    def reference_to_key(self, reference: ResultReference) -> Identifier:
        """Cast the given reference to the key type corresponding to the
        key used in target container.

        The key type for a LinkedContainer is the resultReference. This is a reference
        which does not point to a DataItem directly, but points to some output. In this
        case the 'output' is 'the DataItem that is linked to, transformed'.
        To obtain this original dataItem, we need to find its original name. To
        find its original name, we need to de-pseudonymize it via a keyMap.
        To find the correct KeyMap we need to know the key type.
        An AccessionNumber has a different pseudonym from a report ID, etc.
        """
        # find the key type for the linked Store and convert
        key_type = self.link.get_original_key_type()
        return key_type(reference.value)


    def retrieve(self, key: ResultReference) -> OutputType:
        typed_key = self.reference_to_key(key)
        return self.link.get_data_item(typed_key)


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


class Interface:
    """The space between two domains. Defines how Identifiers and DataItems change
    from one domain to the other.

    Responsibilities
    ----------------
    * In charge of holding all KeyMaps and Links. Interface is the only object
      that can access KeyMaps.
    * Knows the names of the two domains it exists between.
    """

    def __init__(self, domain_a: str, domain_b: str,
                 key_file: KeyFile,
                 links:List[Link]=None,
                 ):
        self.domain_a = domain_a
        self.domain_b = domain_b
        self.key_file = key_file

        if links is None:
            links = []
        self.links = links

    def retrieve_counterpart(self, domain_name: str, key: KeyType) -> KeyType:
        """Retrieve the counterpart to key from domain"""
        return self.key_file.retrieve_counterpart(domain_name, key)