import fnmatch

from auto.naming.naming import Naming

type_to_type = {
    "Group": "asg",
    "Instance": "ec2",
    "Listener": "lsr",
    "Record": "rcd",
    "Role": "iam",
    "SubnetGroup": "sng",
}


class DefaultNaming(Naming):
    def __init__(self,
                 product_code: str,
                 static_environment_name: str):
        self.product_code = product_code
        self.static_environment_name = static_environment_name

        self.logical_names = set()

    def get_name(self, resource_unique_type_name: str) -> str:
        result = self.parse_resource_unique_type_name(resource_unique_type_name)

        resource_type = result.type
        if result.type in type_to_type:
            resource_type = type_to_type[resource_type]
        else:
            resource_type = result.type_short

        return self.get_logical_name(f"{self.product_code}-{self.static_environment_name[0]}-{resource_type}")

    def get_logical_name(self, logical_name: str):
        logical_name_count = self.get_logical_name_count(f"{logical_name}-*")
        logical_name_count += 1
        logical_name = f"{logical_name}-{logical_name_count:03d}"
        self.logical_names.add(logical_name)

        return logical_name

    def get_logical_name_count(self, logical_name: str) -> int:
        count = 0
        for n in self.logical_names:
            if fnmatch.fnmatch(n, logical_name):
                count += 1
        return count
