import pytest

from clictree.keyfiles import DictKeyFile


def test_keyfile():
    key_file = DictKeyFile(mapping={"5": "patient1", "9": "patient2"})
    assert key_file.retrieve_pseudonym("5") == "patient1"
    with pytest.raises(KeyError):
        key_file.retrieve_pseudonym("2")

    assert key_file.retrieve_original("patient2") == "9"
    with pytest.raises(KeyError):
        key_file.retrieve_original("unknown")