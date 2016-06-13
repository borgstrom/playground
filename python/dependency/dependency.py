"""Dependency.  It's no joke."""

import glob
import json
import os
import semantic_version
import six
import weakref

from collections import deque


class DependencyException(Exception):
    """Base class for all dependency exceptions"""
    def __init__(self, product):
        self.product = product
        self.message = repr(self)


class UnknownProduct(DependencyException):
    """We don't know about a given product"""
    def __repr__(self):
        return 'Unknown product: {}'.format(self.product)


class UnresolvableVersion(DependencyException):
    """We could not resolve a version for a specific product"""
    def __repr__(self):
        return 'Unresolvable version "{}" for product: {}'.format(self.product.target, self.product)


class VersionConflict(DependencyException):
    """There was a conflict resolving a version spec for a product"""
    def __init__(self, product, conflict_target):
        super(VersionConflict, self).__init__(product)
        self.conflict_target = conflict_target

    def __str__(self):
        return 'Version conflict for {}.  Selected {}, wanted {}'.format(self.product,
                                                                         self.product.selected,
                                                                         self.conflict_target)


class Spec(semantic_version.Spec):
    """Custom Spec that converts x.y.* wildcards to >=x.y.0,<x.(y+1).0"""

    @classmethod
    def parse(cls, specs_string, **kwargs):
        if '*' in specs_string:
            specs_string = cls.parse_wildcard(specs_string)
        return super(Spec, cls).parse(specs_string, **kwargs)

    @classmethod
    def parse_wildcard(self, specs_string):
        parts = specs_string.split('.')
        if len(parts) != 3 or parts[2] != '*':
            raise ValueError('Wildcards are only supported as x.y.*, "{}" is invalid'.format(specs_string))

        lowest = '.'.join([parts[0], parts[1], '0'])
        highest = '.'.join([parts[0], str(int(parts[1]) + 1), '0'])
        return '>={},<{}'.format(lowest, highest)


class Product(object):
    """ XXX TODO """
    _instances = None

    def __new__(cls, name, version, *args, **kwargs):
        if cls._instances is None:
            cls._instances = {}

        if name not in cls._instances:
            cls._instances[name] = {}

        if version not in cls._instances[name]:
            cls._instances[name][version] = super(Product, cls).__new__(cls, name, version, *args, **kwargs)

        return cls._instances[name][version]

    def __init__(self, name, version):
        self.name = name
        self.version = version
        self.dependencies = weakref.WeakSet()

    def add_dependency(self, product):
        self.dependencies.add(product)

    @classmethod
    def load(cls, directory):
        """Load all of the definitions in given directory"""
        for definition in glob.glob(os.path.join(directory, "*.json")):
            with open(definition, 'r') as definition_fd:
                definition_data = json.load(definition_fd)
                
                for version, deps in six.iteritems(definition_data.get('versions', {})):
                    obj = cls(definition_data['name'], version)
                    for dep_name, dep_ver in six.iteritems(deps):
                        dep_obj = cls(dep_name, dep_ver)
                        obj.add_dependency(dep_obj)

    @classmethod
    def save(cls, directory):
        """Save all of the definitions to the given directory"""
        for name, versions in six.iteritems(cls._instances):
            definition = os.path.join(directory, "{}.json".format(name))
            with open(definition, 'w') as definition_fd:
                definition_data = {
                    'name': name,
                    'versions': dict(
                        (product.version, dict(
                            (dep.name, dep.version)
                            for dep in product.dependencies
                        ))
                        for product in six.itervalues(versions)
                    )
                }
                json.dump(definition_data, definition_fd, sort_keys=True, indent=4)

    @classmethod
    def get(cls, name, version):
        return cls._instances.get(name, {}).get(version)

    @classmethod
    def get_all_versions(cls, name):
        return cls._instances.get(name, {})

    @classmethod
    def exists(cls, name):
        return name in cls._instances

    @classmethod
    def resolve_version(cls, name, spec):
        """Given a semver spec find a matching version in our versions, if possible."""
        # special case, an empty string means all versions
        if spec == '':
            spec = '>=0.0.0'

        target = Spec(spec)
        return target.select([
            semantic_version.Version(version, partial=True)
            for version in six.iterkeys(cls.get_all_versions(name))
        ])


class VersionCatalog(object):
    """ XXX TODO """

    def __init__(self, catalog):
        """Initialize this catalog

        :param dict catalog: A mapping of {'product': {'x.y.z': {'dependency': 'spec'}}}
        """
        self.products = {}
        for product, versions in six.iteritems(catalog):
            self.products[product] = dict(
                (version, Product(product, version, dependencies=dependencies))
                for version, dependencies in six.iteritems(versions)
            )

    def resolve(self, spec, resolved=None):
        """Given a specification of products and versions along with a catalog, resolve the full list of dependencies.

        :param dict spec: A mapping of 'product':'spec' entries to resolve
        :param dict resolved: None or a dict of already resolved 'product':'version' entries
        """
        if not resolved:
            resolved = {}

        dependencies = []

        for name, version_spec in six.iteritems(spec):
            if name not in self.products:
                raise UnknownProduct(name)

            if name in resolved:
                # we've resolved this product already, ensure this target is inline with what we've resolved
                spec = Spec(version_spec)
                if not spec.match(resolved[name].selected):
                    raise VersionConflict(resolved[name], version_spec)

                # we're good, jump to the next spec item
                continue

            version = Product.resolve_version(name, version_spec)
            if not version:
                raise UnresolvableVersion(name)

            # we've found the version for this product
            version = str(version)
            resolved[name] = self.products[version]

            # queue dependencies
            dependencies.append(name)

        # process dependencies
        for dependency_spec in dependencies:
            resolved.update(self.resolve(dependency_spec, resolved))

        return resolved
