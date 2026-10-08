import pydicom

from abc import ABC, abstractmethod
from typing import Generic, Iterator, TypeVar


# in clictree all studies are represented by pydicom datasets
Instance = pydicom.Dataset

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

class Repository(ABC, Generic[KeyType, OutputType]):
    """A thing that can provide a specific dataitem by key"""
    @abstractmethod
    def retrieve(self, key: KeyType) -> OutputType:
        pass

class Source(ABC, Generic[OutputType]):
    """A thing that you can retrieve data items from without a key"""

    @abstractmethod
    def __iter__(self) -> Iterator[OutputType]:
        pass


class Store(ABC, Generic[InputType, KeyType]):

    @abstractmethod
    def write(self, data_item: InputType) -> KeyType:
        pass
