"""Everything that can serve as a unique identifier for something in CLICTree

Location Hierarchy
------------------
To point to a data item, 4 levels are important:
DataTtem <-  Collection <- Domain <- Context

* A DataItem represents one piece of data
* A Collection contains references to data items
* A Domain can contain multiple collections, and represents a pseudonymization domain
* A Context is linked to authentication. The context determines which resources,
  credentials are available.

"""
from itertools import dropwhile


class Identifier:
    """A key to identify a single thing"""
    def __init__(self, value:str):
        self.value = value

    def __str__(self):
        return f"{type(self).__name__} : {self.value}"


class URI:
    """Identifies a location or object.

    Can be absolute or relative. An absolute URI uniquely
    identifies a single data item within a context

    Partial URIs identify a data item at lower levels in the location hierarchy.

    Properties
    ----------
    A URI should be serializable to string

    Location elements can be empty, but have to be consecutive.
    * <container>:<uid> is a valid URI for a data item within a domain
    * <domain>:<container> is a valid URI for a single container
    * <domain>:<uid> is invalid as the intermediate level <container> is missing.

    Development Notes
    -----------------
    This whole class seems very bloated. Basically it is a string that can be parsed
    and the parsing has a particular structure. Nothing that would require 9+
    subfunctions. Investigate whether this can be done better with pydantic and possibly
    a parsing definition language. Is LARK overkill?
    """

    SEPARATOR = "/"
    ROOT_INDICATOR = "/"

    def __init__(self, context_name: str, domain_name, container_name: str,
                 data_item_uid: str):
        self.context_name = context_name
        self.domain_name = domain_name
        self.container_name = container_name
        self.data_item_uid = data_item_uid

    def __eq__(self, other):
        return self.as_tuple() == other.as_tuple()

    def __hash__(self):
        """A URI is fully described by its string value"""
        return hash(self.to_string())

    @classmethod
    def is_root(cls, string_in):
        """This string denotes a URI starting at root. It is not relative"""
        return string_in.startswith(cls.ROOT_INDICATOR)

    @classmethod
    def from_string(cls, string_in):
        """Parse UID from string

        Format
        ------
        /<context>/<domain>/<container>/<uid>
        Slash-separated. Initial slash denotes root level.
        uri without root is assumed to be partial, and filled from right to left.
        For example "boo/faz" is a partial URI for a container 'boo' containg item
        'faz', while "/boo/faz" is absolute, denoting a context 'boo' containing a
        domain 'faz'

        Raises
        ------
        ValueError
            If string cannot be parsed
        """

        if cls.is_root(string_in):
            # this is an absolute path. Fill context and subsequent elements
            parsed = cls.from_tuple(
                rpad(string_in.lstrip(
                    cls.ROOT_INDICATOR).split(cls.SEPARATOR),4,fill=None))

        else:
            # this is relative. Fill uid and anything before that
            parsed = cls.from_tuple(lpad(string_in.split(cls.SEPARATOR), 4, fill=None))

        if parsed.is_valid():
            return parsed
        else:
            raise ValueError(f"Parsed URI {parsed} is not valid")

    @classmethod
    def from_tuple(cls, tuple_in):
        """Expects exactly size-4 tuple. None values allowed"""
        context, domain, container, uid = tuple_in
        return cls(context, domain, container, uid)

    def to_string(self) -> str:
        uri = self.SEPARATOR.join(trim_none(self.as_tuple()))
        if self.is_absolute():
            uri = self.ROOT_INDICATOR + uri
        return uri


    def as_tuple(self):
        return (self.context_name, self.domain_name, self.container_name,
                self.data_item_uid)

    def is_absolute(self) -> bool:
        """This URI starts at the widest location level: context. Is not relative."""
        return bool(self.context_name)

    def is_data_item_reference(self):
        """This URI references a data item, not a higher-level location"""
        return bool(self.data_item_uid)

    def is_consecutive(self) -> bool:
        """Running through location hierarchy from left to right, they form a
        consecutive block without holes
        """
        return any(x for x in trim_none(self.as_tuple) if x is None)

    def is_valid(self):
        """Check whether this uri points to either a location or a data item"""
        if self.is_consecutive and (self.is_absolute or self.is_data_item_reference):
            return True
        else:
            return False


    def __str__(self):
        return self.to_string()

    def __repr__(self):
        # a URI with the same string value really should be the same object. There
        # are no hidden variables.
        return self.to_string()

def trim_none(tuple_in):
    """Remove any None values from both sides of a tuple"""
    tuple_in = tuple(dropwhile(lambda x: x is None, tuple_in))  # trim left
    return tuple(dropwhile(lambda x: x is None, reversed(tuple_in)))[::-1]  # trim right

def lpad(tuple_in, size:int, fill=None):
    """Enlarge tuple to be size. Fill with filler on the left if needed"""
    return (fill,) * (size - len(tuple_in)) + tuple(tuple_in)

def rpad(tuple_in, size:int , fill=None):
    """Enlarge tuple to be size. Fill with filler on the right if needed"""
    return tuple(tuple_in) + (fill,) * (size - len(tuple_in))

class DICOMStudyIdentifier(Identifier):
    """A key to identify a single DICOM study"""
    pass

class StudyInstanceUID(DICOMStudyIdentifier):
    pass

class AccessionNumber(DICOMStudyIdentifier):
    pass

class PatientIdentifier(Identifier):
    pass

UNKNOWN_PATIENT = PatientIdentifier(value='Unknown')  # Default patient