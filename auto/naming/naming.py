from abc import abstractmethod, ABC
from collections import namedtuple


class Naming(ABC):
    @abstractmethod
    def get_name(self,
                 resource_unique_type_name: str) -> str:
        pass

    def parse_resource_unique_type_name(self, resource_unique_type_name: str):
        split = resource_unique_type_name.split(":")
        Tuple = namedtuple("Tuple", ["pkg", "module", "type", "type_short"])
        type_short = self.get_resource_type_short(split[2]).lower()

        return Tuple(split[0], split[1], split[2], type_short)

    def get_resource_type_short(self, resource_type: str):
        uppers = [char for char in resource_type if char.isupper()]
        temp = ""
        return temp.join(uppers)
