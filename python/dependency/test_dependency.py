import unittest

from .dependency import Product, Spec, UnknownProduct, VersionCatalog, VersionConflict

VERSION_CATALOG = {
    # foo has no deps
    'foo': {
        '1.0.0': {},
        '1.0.1': {},
        '2.0.0': {},
    },

    # bar deps on foo
    'bar': {
        '1.1.0': {'foo': '1.0.*'},
        '1.1.1': {'foo': '1.0.*'},
        '1.1.2': {'foo': '1.0.*'},
        '1.2.0': {'foo': '2.0.*'},
        '1.3.0': {'foo': '2.0.*'},
        '2.0.0': {'foo': '2.0.*'},
    },

    # baz deps on bar
    'baz': {
        '1.6.9': {'bar': '1.1.*'},
        '1.6.10-beta': {'bar': '1.1.*'},
        '1.6.10': {'bar': '1.1.*'},
    },

    # lorem deps on bar & baz
    'lorem': {
        '4.2.1': {'bar': '1.1.*', 'baz': '1.6.*'},
    },

    # ipsum deps on baz & lorem
    'ipsum': {
        '3.3.1': {},
        '3.3.2': {'baz': '1.6.*', 'lorem': '4.2.*'},
    },

    # dolor deps on bar, & ipsum
    'dolor': {
        '7.1.0': {},
        '7.2.0': {},
        '7.2.1': {'bar': '1.1.*', 'ipsum': '3.3.*'},
        '7.3.0': {},
    },

    # recursion
    'loop-y': {
        '1.0.0': {'loop-z': '1.0.*'},
    },
    'loop-z': {
        '1.0.0': {'loop-y': '1.0.*'},
    },
}


class VersionCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = VersionCatalog(VERSION_CATALOG)

    def test_unknown_product(self):
        """Unknown products should raise UnknownProduct"""
        self.assertRaises(UnknownProduct, lambda: self.catalog.resolve(dict(unknown='1.0.0')))

    def test_simple_resolution(self):
        """Straight forward resolution without any dependencies"""
        self.assertEqual(self.catalog.resolve({'foo': '1.0.*'}), {'foo': '1.0.1'})

    def test_good_resolution(self):
        """Given a good, and simple, spec we should resolve the full list of transitive dependencies"""
        deps = {
            'dolor': '7.2.*',
        }
        self.assertEqual(self.catalog.resolve(deps), {
            'dolor': '7.2.1',
            'bar': '1.1.2',
            'foo': '1.0.1',
            'ipsum': '3.3.2',
            'baz': '1.6.10',
            'lorem': '4.2.1'
        })

    def test_invalid_resolution(self):
        """When we specify an invalid spec a VersionConflict should be raised"""
        deps = {
            'dolor': '7.2.*',
            'foo': '2.0.0'
        }

        # this will fail because we have explicitly asked for foo 2.0.0 but dolor want's to pull in 1.0.*
        with self.assertRaises(VersionConflict) as cm:
            self.catalog.resolve(deps)

        self.assertEqual(cm.exception.product.name, 'foo')
        self.assertEqual(str(cm.exception.product.target), '==2.0.0')
        self.assertEqual(str(cm.exception.product.selected), '2.0.0')


    def test_recurision(self):
        """We should break loops without a problem"""
        deps = {
            'loop-y': '1.0.*',
        }
        resolved = self.catalog.resolve(deps)
        self.assertEqual(resolved, {
            'loop-y': '1.0.0',
            'loop-z': '1.0.0'
        })


class SpecTests(unittest.TestCase):
    def test_parse_wildcard(self):
        """Valid wildcards should expand to the expected values"""
        self.assertEqual(Spec.parse_wildcard('1.0.*'), '>=1.0.0,<1.1.0')
        self.assertEqual(Spec.parse_wildcard('14.99.*'), '>=14.99.0,<14.100.0')

    def test_parse_invalid_wildcard(self):
        """Invalid wildcards should raise ValueError"""
        self.assertRaises(ValueError, lambda: Spec.parse_wildcard('1.*.0'))
        self.assertRaises(ValueError, lambda: Spec.parse_wildcard('1.0.*,1.1.*'))


class ProductTests(unittest.TestCase):
    def test_basic(self):
        foo = Product("foo", "1.0.0")
        foo2 = Product("foo", "2.0.0")

        bar = Product("bar", "2.0.5")
        foo.add_dependency(bar)
        foo2.add_dependency(bar)

        baz = Product("baz", "4.5.6")
        bar.add_dependency(baz)

        lol = Product("lol", "999.99.1")
        foo2.add_dependency(lol)

        # since we cache our instances the should be identical
        self.assertEqual(id(foo), id(Product("foo", "1.0.0")))
