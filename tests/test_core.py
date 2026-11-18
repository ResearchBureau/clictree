
from clictree.core import Context, Domain, Interface, KeyFile, Channel, LinkedContainer, \
    TransformedStore
from clictree.identifiers import AccessionNumber, URI
from clictree.keyfiles import AccessionNumberMap, MemoryOnlyBackend, \
    PatientIdentifierMap
from tests.factories import PatientChanger, SimpleLink, SimpleStore


def test_domain_basic():
    """Simplest use of domain. Download one thing from a store"""

    domain = Domain()
    a_store = SimpleStore()

    domain.register_container(a_store,"VNA")
    data = domain.get_data_item(URI.from_string("VNA:study_A"))

    studies = [x for x in data.data]
    assert len(studies) == 3
    assert studies[1].SOPInstanceUID == "2"

def test_domain_pipeline():
    """Try to download something that requires chaining through a channel"""

    # create a domain
    domain = Domain()

    # With a store that yields datasets for whatever key you ask it for
    a_store = SimpleStore()
    domain.register_container(a_store, "STORE")

    # And something which transforms. Just adds _MODIFIED to patientID
    transformed = TransformedStore(data_source=a_store, transformation=PatientChanger())
    domain.register_container(transformed, "TRANSFORMED")

    # Now you should be able to ask the domain for this URI
    data = domain.get_data_item(URI.from_string("TRANSFORMED:1234"))
    studies = [x for x in data.data]

    # and the domain should be able to figure out what is needed, obtain source,
    # run transformation
    assert len(studies) == 3
    assert studies[1].PatientID == "Patient_1_MODIFIED"
    assert studies[1].StudyInstanceUID == "1234"


def test_context_pipeline():
    """Try to download something from a different domain through a Channel
    """

    # a context with a clinical domain and a user domain
    context = Context(
        domains={"CLINICAL":Domain(containers={"VNA":SimpleStore()}),
                 "USER":Domain()}
    )

    # I want to transfer data between clinical and user domain. Create an interface
    # that can translate AccessionNumbers

    key_file = KeyFile()
    backend = MemoryOnlyBackend()
    key_file.add_map(AccessionNumberMap(backend=backend, domain_a="CLINICAL",
                                        domain_b="USER"))

    interface = Interface(domain_a="CLINICAL", domain_b="USER",key_file=key_file)
    context.add_interface(interface)  # make available in context

    # add some accession number translations CLINICAL: USER
    backend.insert_batch(values={"1234":"acc_1",
                                 "4567":"acc_2",
                                 "8901":"acc_3",},key_type=AccessionNumber)

    # From user domain I want to obtain some data. Create a channel in interface.
    vna_link = Channel(data_source_container=URI(domain_name="CLINICAL",
                                                 container_name="VNA"),
                       destination_domain="USER",
                       context=context)
    # use only accession numbers to communicate with VNA. TODO: include this in Channel?
    vna_link.get_original_key_type = lambda: AccessionNumber

    interface.channels.append(vna_link)

    # Create a LinkedContainer in USER domain to attach the channel to
    context.domains["USER"].containers["LINKED"] = LinkedContainer(channel=vna_link)

    # now try to obtain some data from USER domain via the channel.
    user_domain = context.domains["USER"]

    studies = user_domain.get_data_item(URI.from_string("LINKED:acc_3"))
    data = [x for x in studies.data]  # expand iterator

    assert data[1].StudyInstanceUID == "8901"
