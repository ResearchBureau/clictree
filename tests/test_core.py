import pytest

from clictree.core import Domain
from clictree.identifiers import URI
from clictree.keyfiles import DictKeyFile
from tests.factories import PatientChanger, SimpleStore


def test_keyfile():
    key_file = DictKeyFile(mapping={"5": "patient1", "9": "patient2"})
    assert key_file.retrieve_pseudonym("5") == "patient1"
    with pytest.raises(KeyError):
        key_file.retrieve_pseudonym("2")

    assert key_file.retrieve_original("patient2") == "9"
    with pytest.raises(KeyError):
        key_file.retrieve_original("unknown")

def test_domain_basic():
    """Simplest use of domain. Download one thing from a store"""

    domain = Domain()
    a_store = SimpleStore()

    domain.register_container(a_store,"VNA")
    data = domain.get_data_item(URI.from_string("VNA/study_A"))

    studies = [x for x in data.data]
    assert len(studies) == 3
    assert studies[1].SOPInstanceUID == "2"

def test_domain_pipeline():
    """Try to download something that requires chaining through a pipeline"""

    # create a domain
    domain = Domain()

    # With a store that yields datasets
    a_store = SimpleStore()
    domain.register_container(a_store, "STORE")

    # And something which transforms
    a_transformation = PatientChanger()
    domain.register_container(a_transformation, "TRANSFORMED")

    # Link transformation to Store.
    # if you want TRANSFORMED:studyA, you need to feed in VNA/studyA
    domain.register_transformation(URI.from_string("TRANSFORMED/studyA"),
                                   URI.from_string("STORE/studyA"))
    # todo: do some type checking, fail if input/output do not match

    # Now you should be able to ask the domain for this URI
    data = domain.get_data_item(URI.from_string("TRANSFORMED/studyA"))
    studies = [x for x in data.data]

    # and the domain should be able to figure out what is needed.
    assert len(studies) == 3
    assert studies[1].PatientID == "Patient_1_MODIFIED"








