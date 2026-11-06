import pytest

from clictree.identifiers import AccessionNumber, PatientIdentifier
from clictree.keyfiles import AccessionNumberMap, MemoryOnlyBackend, \
    PatientIdentifierMap
from clictree.core import KeyFile


def test_keyfile():
    """Check some basic KeyFile interactions"""

    # set up keyfile that saves to memory and can handle
    # patientIdentifier and AccessionNumber
    domain_a = "original"
    domain_b = "derived"

    backend = MemoryOnlyBackend()
    patient_map = PatientIdentifierMap(backend=backend, domain_a=domain_a,
                                       domain_b=domain_b)
    acc_map = AccessionNumberMap(backend=backend, domain_a=domain_a,
                                 domain_b=domain_b)

    key_file = KeyFile()
    key_file.add_map(patient_map)
    key_file.add_map(acc_map)

    # seed some values
    backend.insert(key_a=PatientIdentifier('John'),key_b=PatientIdentifier('Patient_1'))
    backend.insert(key_a=PatientIdentifier('Sue'), key_b=PatientIdentifier('Patient_2'))
    backend.insert(key_a=AccessionNumber('123'), key_b=AccessionNumber('study_1'))

    # check retrieval
    pseudonym = key_file.retrieve_counterpart(domain_name=domain_a,
                                              key=PatientIdentifier("John"))
    assert pseudonym.value == 'Patient_1'
    assert key_file.retrieve_counterpart(
        domain_name=domain_a,key=AccessionNumber("123")).value == "study_1"

    # and the other way around
    pseudonym = key_file.retrieve_counterpart(domain_name=domain_b,
                                              key=PatientIdentifier("Patient_2"))
    assert pseudonym.value == 'Sue'

    # unknown values raise KeyError
    with pytest.raises(KeyError):
        key_file.retrieve_counterpart(domain_name=domain_b,
                                  key=PatientIdentifier("unknown"))

    # unknown domains raise valueError
    with pytest.raises(ValueError):
        key_file.retrieve_counterpart(domain_name="Unknown",
                                  key=PatientIdentifier("Patient_1"))

    # using wrong KeyType
    with pytest.raises(KeyError):
        key_file.retrieve_counterpart(domain_name=domain_b,
                                  key=AccessionNumber("Patient1"))

