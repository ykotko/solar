import os

from solar.core.resource import virtual_resource as vr
from solar.core import signals
from solar.events.api import add_event
from solar.events import controls


class BaseTemplate(object):
    @staticmethod
    def args_fmt(args, kwargs):
        return {
            k.format(**kwargs): v.format(**kwargs) for k, v in args.items()
        }

    @staticmethod
    def action_state_parse(action_state):
        action, state = action_state.split('/')

        return {
            'action': action,
            'state': state,
        }


class ResourceTemplate(BaseTemplate):
    def __init__(self, resource):
        self.resource = resource

    def connect_list(self, resources, args={}):
        for receiver_num, resource in enumerate(resources.resources):
            kwargs = {
                'receiver_num': receiver_num,
            }

            args_fmt = self.args_fmt(args, kwargs)

            signals.connect(self.resource, resource, args_fmt)


class ResourceListTemplate(BaseTemplate):
    def __init__(self, resources):
        self.resources = resources

    @classmethod
    def create(cls, count, resource_path, args={}):
        created_resources = []

        resource_path_name = os.path.split(resource_path)[-1]

        for num in range(count):
            kwargs = {
                'num': num,
                'resource_path_name': resource_path_name,
                }
            kwargs['name'] = '{resource_path_name}-{num}'.format(**kwargs)

            args_fmt = cls.args_fmt(args, kwargs)

            r = vr.create('{name}'.format(**kwargs),
                          resource_path,
                          args_fmt)[0]

            created_resources.append(r)

        return ResourceListTemplate(created_resources)

    def add_deps(self, action_state, resources, action):
        action_state = self.action_state_parse(action_state)

        for r, dep_r in zip(self.resources, resources.resources):
            add_event(
                controls.Dep(
                    r.name,
                    action_state['action'],
                    action_state['state'],
                    dep_r.name,
                    action
                )
            )

    def add_react(self, action_state, resource, action):
        action_state = self.action_state_parse(action_state)

        for r in self.resources:
            add_event(
                controls.React(
                    r.name,
                    action_state['action'],
                    action_state['state'],
                    resource.resource.name,
                    action
                )
            )

    def add_reacts(self, action_state, resources, action):
        action_state = self.action_state_parse(action_state)

        for r, react_r in zip(self.resources, resources.resources):
            add_event(
                controls.React(
                    r.name,
                    action_state['action'],
                    action_state['state'],
                    react_r.name,
                    action
                )
            )

    def filter(self, func):
        resources = filter(func, self.resources)

        return ResourceListTemplate(resources)

    def connect_list_to_each(self, resources, args={}):
        for emitter_num, emitter in enumerate(self.resources):
            for receiver_num, receiver in enumerate(resources.resources):
                kwargs = {
                    'emitter_num': emitter_num,
                    'receiver_num': receiver_num,
                }

                args_fmt = self.args_fmt(args, kwargs)

                signals.connect(emitter, receiver, args_fmt)

    def on_each(self, resource_path, args={}):
        created_resources = ResourceListTemplate.create(
            len(self.resources),
            resource_path,
            args
        )

        for i, resource in enumerate(self.resources):
            signals.connect(resource, created_resources.resources[i])

        return created_resources

    def take(self, i):
        return ResourceTemplate(self.resources[i])


def nodes_from(template_path):
    nodes = vr.create('nodes', template_path, {})
    return ResourceListTemplate(nodes)