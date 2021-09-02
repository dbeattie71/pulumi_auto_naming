import copy
from typing import Optional, cast

from pulumi import ResourceOptions, _types, ResourceTransformationArgs, Resource
from pulumi.resource import inherited_child_alias, collapse_alias_to_urn, DependencyResource
from pulumi.runtime import get_root_resource
from pulumi.runtime.resource import convert_providers, get_resource, read_resource, register_resource


def __init__(self,
             t: str,
             name: str,
             custom: bool,
             props: Optional['Inputs'] = None,
             opts: Optional[ResourceOptions] = None,
             remote: bool = False,
             dependency: bool = False) -> None:
    """
    :param str t: The type of this resource.
    :param str name: The name of this resource.
    :param bool custom: True if this resource is a custom resource.
    :param Optional[Inputs] props: An optional list of input properties to use as inputs for the resource.
           If props is an input type (decorated with `@input_type`), dict keys will be translated using
           the type's and resource's type/name metadata rather than using the `translate_input_property`
           and `translate_output_property` methods.
    :param Optional[ResourceOptions] opts: Optional set of :class:`pulumi.ResourceOptions` to use for this
           resource.
    :param bool remote: True if this is a remote component resource.
    :param bool dependency: True if this is a synthetic resource used internally for dependency tracking.
    """

    if dependency:
        self._protect = False
        self._providers = {}
        return

    if props is None:
        props = {}
    if not t:
        raise TypeError('Missing resource type argument')
    if not isinstance(t, str):
        raise TypeError('Expected resource type to be a string')
    # if not name:
    #     raise TypeError('Missing resource name argument (for URN creation)')
    if not isinstance(name, str):
        raise TypeError('Expected resource name to be a string')
    if opts is None:
        opts = ResourceOptions()
    elif not isinstance(opts, ResourceOptions):
        raise TypeError('Expected resource options to be a ResourceOptions instance')

    # If `props` is an input type, convert it into an untranslated dictionary.
    # Translation of the keys will happen later using the type's and resource's type/name metadata.
    # If `props` is not an input type, set `typ` to None to make translation behave as it has previously.
    typ = type(props)
    if _types.is_input_type(typ):
        props = _types.input_type_to_untranslated_dict(props)
    else:
        typ = None  # type: ignore

    # Before anything else - if there are transformations registered, give them a chance to run to modify the user
    # provided properties and options assigned to this resource.
    parent = opts.parent
    if parent is None:
        parent = get_root_resource()
    parent_transformations = (parent._transformations or []) if parent is not None else []
    self._transformations = (opts.transformations or []) + parent_transformations
    for transformation in self._transformations:
        args = ResourceTransformationArgs(resource=self, type_=t, name=name, props=props, opts=opts)
        tres = transformation(args)
        if tres is not None:
            if tres.opts.parent != opts.parent:
                # This is currently not allowed because the parent tree is needed to establish what
                # transformation to apply in the first place, and to compute inheritance of other
                # resource options in the Resource constructor before transformations are run (so
                # modifying it here would only even partially take affect).  It's theoretically
                # possible this restriction could be lifted in the future, but for now just
                # disallow re-parenting resources in transformations to be safe.
                raise Exception("Transformations cannot currently be used to change the `parent` of a resource.")
            props = tres.props
            opts = tres.opts
            if hasattr(tres, "name"):
                name = tres.name

    self._name = name

    if not name:
        raise TypeError('Missing resource name argument (for URN creation)')

    # Make a shallow clone of opts to ensure we don't modify the value passed in.
    opts = copy.copy(opts)

    self._providers = {}
    # Check the parent type if one exists and fill in any default options.
    if opts.parent is not None:
        if not isinstance(opts.parent, Resource):
            raise TypeError("Resource parent is not a valid Resource")

        # Infer protection from parent, if one was provided.
        if opts.protect is None:
            opts.protect = opts.parent._protect

        # Make a copy of the aliases array, and add to it any implicit aliases inherited from
        # its parent
        if opts.aliases is None:
            opts.aliases = []

        opts.aliases = opts.aliases.copy()
        for parent_alias in opts.parent._aliases:
            child_alias = inherited_child_alias(
                name, opts.parent._name, parent_alias, t)
            opts.aliases.append(cast('Output[Union[str, Alias]]', child_alias))

        # Infer providers and provider maps from parent, if one was provided.
        self._providers = opts.parent._providers

    if custom:
        provider = opts.provider
        if provider is None:
            if not opts.parent is None:
                # If no provider was given, but we have a parent, then inherit the
                # provider from our parent.
                opts.provider = opts.parent.get_provider(t)
        else:
            # If a provider was specified, add it to the providers map under this type's package
            # so that any children of this resource inherit its provider.
            type_components = t.split(":")
            if len(type_components) == 3:
                [pkg, _, _] = type_components
                self._providers = {**self._providers, pkg: provider}
    else:
        providers = convert_providers(opts.provider, opts.providers)
        self._providers = {**self._providers, **providers}

    self._protect = bool(opts.protect)

    # Collapse any `Alias`es down to URNs. We have to wait until this point to do so because we
    # do not know the default `name` and `type` to apply until we are inside the resource
    # constructor.
    self._aliases: 'List[Input[str]]' = []
    if opts.aliases is not None:
        for alias in opts.aliases:
            self._aliases.append(collapse_alias_to_urn(
                alias, name, t, opts.parent))

    if opts.urn is not None:
        # This is a resource that already exists. Read its state from the engine.
        get_resource(self, props, custom, opts.urn, typ)
    elif opts.id is not None:
        # If this is a custom resource that already exists, read its state from the provider.
        if not custom:
            raise Exception(
                "Cannot read an existing resource unless it has a custom provider")
        read_resource(cast('CustomResource', self), t, name, props, opts, typ)
    else:
        register_resource(self, t, name, custom, remote, DependencyResource, props, opts, typ)
