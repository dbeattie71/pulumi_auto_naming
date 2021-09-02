from pulumi import ResourceTransformationArgs

from auto.naming.naming import Naming


class PassThroughNaming(Naming):
    def get_name(self,
                 args: ResourceTransformationArgs) -> str:
        return args.name
