"""
Contains templates for metagpt roles.
"""

import re
import asyncio
import typing
from random import choice

from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
import json


class BaseRole(Role):
    """
    Base Role class
    """
    name: str = "Bob"
    profile: str = 'BaseRole'

    def __init__(self, actions: list[type(Action)], autoflush: bool = False, **kwargs):
        """
        Constructor for BaseRole class

        :param autoflush: whether to clear the context after each action
        """
        super().__init__(**kwargs)
        self.set_actions(actions)

        self.action_context: dict = dict()
        self.autoflush: bool = autoflush

        self.set_name()

    def set_name(self):
        # set a funky name
        names = [
            'Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Thomas',
            'Hannah', 'Ivy', 'Jack', 'Katie', 'Liam', 'Mia', 'Noah', 'Olivia', 'Zaid',
            'Parker', 'Quinn', 'Ryan', 'Sophia', 'Tyler', 'Uma', 'Victor', 'Willow',
        ]
        setattr(self.__class__, 'name', choice(names))

    async def run(self):
        for action in self.actions:
            self.rc.todo = action
            rsp = await self._act()
            #self.rc.memory.append(rsp)
        return rsp

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        #memory = self.rc.memory[-1]

        rsp = await todo.run(**self.action_context)
        msg = Message(content=rsp, role=self.profile, cause_by=todo)

        if self.autoflush: self.action_context = dict()
        return msg


class BaseDynamicAction(Action):
    """
    Base Action class for dynamic action generation
    """
    async def run(self, **kwargs):
        logger.info(f'Action \'{self.__class__.__name__}\': run with kwargs {kwargs}')
        prompt = self.prompt_template.format(**kwargs)
        rsp = await self._aask(prompt)
        result = type(self).match_pattern(rsp)
        return result
