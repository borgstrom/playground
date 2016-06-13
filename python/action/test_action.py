from collections import deque

from .action import Action


def test_action_resolution():
    """Ensure our action resolution works"""
    actions = [
        Action('build'),
        Action('deps', before='build'),
        Action('foo', after='deps'),
        Action('bar', before='deps'),
        Action('baz', after='bar')
    ]

    assert Action.resolve("deps") == deque([
        "bar",
        "baz",
        "deps",
        "foo"
    ])

    assert Action.resolve("build") == deque([
        "bar",
        "baz",
        "deps",
        "foo",
        "build"
    ])

    assert Action.resolve("foo") == deque([
        "foo"
    ])

    assert Action.resolve("baz") == deque([
        "baz"
    ])

    assert Action.resolve("bar") == deque([
        "bar",
        "baz"
    ])


def test_with_fruit():
    """Mmmmmm... Fruity!"""
    actions = [
        Action(name='apple'),
        Action(name='cherry'),
        Action(name='orange', before='apple'),
        Action(name='pear', after='apple'),
        Action(name='grape', after='orange', before='cherry'),
        Action(name='bannana', before='orange'),
        Action(name='peach', before='pear')
    ]

    assert Action.resolve('apple') == deque([
        'bannana',
        'orange',
        'grape',
        'apple',
        'peach',
        'pear'
    ])

    # grape has a before and after list but nothing lists it in before or after so when resolved it returns itself
    assert Action.resolve('grape') == deque([
        'grape',
    ])

    assert Action.resolve('cherry') == deque([
        'grape',
        'cherry'
    ])
