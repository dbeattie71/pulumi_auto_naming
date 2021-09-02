import pulumi
from pulumi import Resource
from pulumi_aws import autoscaling

from auto import resource_init
from auto.naming.naming import Naming


class AutoNaming:
    def __init__(self, naming: Naming):
        Resource.__init__ = resource_init.__init__
        self.naming = naming

    def register(self):
        pulumi.runtime.register_stack_transformation(lambda args: self.set_name(args))

    def set_name(self, args):
        resource_name = self.naming.get_name(args.type_)
        resource_transformation_result = pulumi.ResourceTransformationResult(args.props, args.opts)
        resource_transformation_result.name = resource_name

        if args.type_ == "aws:autoscaling/group:Group":
            if args.props["tags"] is None:
                args.props["tags"] = []
            args.props["tags"].append(
                autoscaling.GroupTagArgs(key="Name", value=resource_name, propagate_at_launch=True))

        if args.type_ == "aws:ec2/instance:Instance":
            args.props["tags"] = {**args.props["tags"], **{"Name": resource_name}}

        return resource_transformation_result
