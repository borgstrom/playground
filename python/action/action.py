import six

from collections import deque


class Action(object):
    """Represents an action in a graph.

    Each action can specify ordering requirements by expressing which other action(s) it should run before or after.

    All actions created get stored in a singleton instance dict on the main Action class meaning that action names are
    globally unique and if you create a "foo" action and then create another "foo" action the first will be lost.
    """
    _instances = None

    def __init__(self, name, before=None, after=None):
        self.name = name
        self.before = before
        self.after = after

        # add our self to the instance list
        self._add(name, self)

    def __repr__(self):
        return "Action('%s', before=%s, after=%s)" % (self.name, self.before, self.after)

    @classmethod
    def _add(cls, name, obj):
        if not cls._instances:
            cls._instances = {}
        cls._instances[name] = obj

    @classmethod
    def get_all_actions(cls):
        """Return all action names that have been created"""
        if cls._instances:
            return cls._instances.keys()

    @classmethod
    def get(cls, name):
        """Get a specific action by name"""
        if cls._instances:
            return cls._instances.get(name)

    @classmethod
    def resolve(cls, name, seen=None):
        """Given a name this will resolve the full list of actions, in the correct order, and return a list of names"""
        action = cls.get(name)
        resolved = deque()

        if seen is None:
            seen = []
        elif name in seen:
            return []
        seen.append(name)

        def find_in_instances(find_name, attr):
            """Closure to find the current name in our instances based on the named attr."""
            return [
                other_name
                for other_name, other_action in six.iteritems(cls._instances)
                if find_name == getattr(other_action, attr)
            ]
            return found_names

        # find all instances where we are listed in an action's 'before'
        for action_name in find_in_instances(name, 'before'):
            for resolved_name in cls.resolve(action_name, seen=seen):
                resolved.append(resolved_name)

        # add this action
        resolved.append(name)

        # now add all instances where we are listed in an action's 'after'
        for action_name in find_in_instances(name, 'after'):
            for resolved_name in cls.resolve(action_name, seen=seen):
                resolved.append(resolved_name)

        return resolved
