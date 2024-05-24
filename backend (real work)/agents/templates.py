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


class BaseAction(Action):
    """
    Base Action class
    """
    def __init__(self, pattern: str, prompt: str):
        """
        Constructor for BaseAction class

        :param pattern: pattern to match the output
        :param prompt: prompt to ask the agent
        """
        self._pattern = pattern
        self._prompt = prompt

    async def run(self, example: str, instruction: str):
        prompt = self._prompt.format(example=example, instruction=instruction)
        rsp = await self._aask(prompt)
        result = self.parse(rsp)
        return result

    def parse(self, rsp):
        pattern = re.compile(self._pattern, re.DOTALL)
        match = re.search(self._pattern, rsp)
        result = match.group(0) if match else ""
        return result


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


class ChatRole(BaseRole):
    """
    Simple chatbot role
    """
    def __init__(self):
        # get a funky name
        setattr(self.__class__ , 'name', choice(['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace']))