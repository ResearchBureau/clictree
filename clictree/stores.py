"""Things you can save data mapping in"""
from os import PathLike
from pathlib import Path

from dicomtrolley.storage import StorageDir

from clictree.core import InputType, Instance, KeyType, Deposit

class DICOMDiskStorage(Deposit[Instance,Path]):
    """Stores a DICOM instance to a file on disk. Path is based on uids."""

    def __init__(self, root_path: PathLike):
        self.storage = StorageDir(str(root_path))

    def write(self, data_item: InputType) -> KeyType:
        self.storage.save(data_item)
        # storageDir.save does not return anything. Fix when dicomtrolley is updated
