import re
import asyncio
import typing

from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from templates import BaseDynamicAction, BaseRole, ChatRole


def generate_action(name: str, prompt_template: str, output_pattern: str = '.*', classname=None,
                    template: type(Action) = None) -> type(Action):
    """
    Generate a metagpt action class from the given arguments

    :param kwargs: Attributes of action class object
    :return: metagpt action class object
    """

    name = name or 'AgentAction'
    classname = classname or name
    template = template or BaseDynamicAction

    def match_pattern(rsp):
        pattern = re.compile(output_pattern, re.DOTALL)
        match = re.search(pattern, rsp)
        result = match.group(0) if match else rsp
        return result

    action = type(
        classname,
        (template,),
        {
            'match_pattern': staticmethod(match_pattern),
        },
    )

    attributes = {
        'name': name,
        'prompt_template': prompt_template,
    }

    for attribute in attributes:
        setattr(action, attribute, attributes[attribute])

    return action


def generate_role(name: str, actions: list[type(Action)], profile: str = None, classname=None,
                  template: type(Action) = None) -> type(Role):
    """
    Generate a metagpt role class from the given arguments

    :param name: Name of the agent
    :param actions: List of actions for the agent
    :param profile: Profile of the agent, defaults to role name
    :param classname: Name of the class, defaults to 'AgentRole'
    :param template: Template for the role class (superclass), defaults to Role
    :return:
    """

    classname = classname or 'AgentRole'
    profile = profile or classname
    template = template or BaseDynamicRole

    def __init__(self, **kwargs):
        template.__init__(self, **kwargs)
        self.set_actions(actions)

    role = type(
        classname,
        (template,),
        {
            '__init__': __init__,
        },
    )

    attributes = {
        'name': name,
        'profile': profile,
    }

    for attribute in attributes:
        setattr(role, attribute, attributes[attribute])

    return role
