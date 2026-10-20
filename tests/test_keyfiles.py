from clictree.identifiers import PatientIdentifier
from clictree.keyfiles import AccessionNumberMap, KeyFile, MemoryOnlyBackend, \
    PatientIdentifierMap


def test_keyfile():
    """Check basic KeyFile interactions"""

    # set up keyfile that saves to memory and can handle
    # patientIdentifier and AccessionNumber
    backend = MemoryOnlyBackend()
    patient_map = PatientIdentifierMap(backend=backend)
    acc_map = AccessionNumberMap(backend=backend)

    key_file = KeyFile()
    key_file.add_map(patient_map)
    key_file.add_map(acc_map)

    # seed some values
    backend.insert(key=PatientIdentifier('John'),value=PatientIdentifier('Patient_1'))
    backend.insert(key=PatientIdentifier('Sue'), value=PatientIdentifier('Patient_2'))

    # check retrieval
    pseudonym = key_file.retrieve_pseudonym(PatientIdentifier("John"))
    assert pseudonym.value == 'Patient_1'

    assert key_file.retrieve_original(pseudonym).value == "John"



