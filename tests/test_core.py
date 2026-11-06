
from clictree.core import Context, Domain, LinkedContainer, TransformedStore
from clictree.identifiers import URI
from tests.factories import PatientChanger, SimpleLink, SimpleStore


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
    """Try to download something that requires chaining through a link"""

    # create a domain
    domain = Domain()

    # With a store that yields datasets for whatever key you ask it for
    a_store = SimpleStore()
    domain.register_container(a_store, "STORE")

    # And something which transforms. Just adds _MODIFIED to patientID
    transformed = TransformedStore(data_source=a_store, transformation=PatientChanger())
    domain.register_container(transformed, "TRANSFORMED")

    # Now you should be able to ask the domain for this URI
    data = domain.get_data_item(URI.from_string("TRANSFORMED/1234"))
    studies = [x for x in data.data]

    # and the domain should be able to figure out what is needed, obtain source,
    # run transformation
    assert len(studies) == 3
    assert studies[1].PatientID == "Patient_1_MODIFIED"
    assert studies[1].StudyInstanceUID == "1234"


def test_context_pipeline():
    """Try to download something from a different domain through a Link
    """

    # a context with a clinical domain and a user domain
    context = Context(
        domains={"CLINICAL":Domain(containers={"VNA":SimpleStore()}),
                 "USER":Domain()}
    )

    #From user domain I want to obtain some data. Create a link.
    link = SimpleLink(data_source_container=URI.from_string("//CLINICAL/VNA"),context=context)
    context.links.append(link)

    # Create a LinkedContainer in USER domain to attach the link to
    linked = LinkedContainer(link=link)
    context.domains["USER"].containers["LINKED"] = linked

    # now try to obtain some data from USER domain via the link.
    user_domain = context.domains["USER"]
    # any identifier ending in _CHANGED is accepted by SimpleLink()

    """
    studies = user_domain.get_data_item(URI.from_string("LINKED/1122_CHANGED"))
    studies = [x for x in studies.data]  # expand iterator

    assert studies[1].PatientID == "Patient_1"
    assert studies[1].StudyInstanceUID == "1122"
    """