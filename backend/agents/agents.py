from agents.templates import BaseRole, BaseDynamicAction
from metagpt.schema import Message
import json
from rich import print


class ChatAction(BaseDynamicAction):
    """
    Simple chatbot action
    """
    name: str = "Chat"

    async def run(self, prompt: str):
        rsp = await self._aask(prompt)
        return rsp


class ChatRole(BaseRole):
    """
    Simple chatbot role
    """

    def __init__(self):
        super().__init__(actions=[ChatAction])

    def set_history(self, history: list[tuple[str, str]]) -> None:
        """
        Overwrites the message history

        :param history: new message history
        :return: none
        """
        for role, message in history:
            if role == 'User':
                memory = f'\\[Prompt] {message} \\[/prompt]\n'
            elif role == 'Bot':
                memory = f'\\[Answer] {message} \\[/Answer]\n'
            self.rc.memory.add(Message(content=memory, role=role))

    async def run(self, *args, **kwargs) -> Message:
        self.rc.todo = self.actions[0]
        rsp = await self._act(prompt=kwargs.get('prompt'))
        return rsp

    async def _act(self, *args, **kwargs) -> Message:
        todo = self.rc.todo

        user_input = kwargs.get('prompt')
        prompt = (
            """## CHAT HISTORY\n{context}\n## NEW PROMPT FROM USER\n{prompt}\n\nONLY ANSWER THE LATEST PROMPT:\n"""
            .format(context=self.get_chat_history(), prompt=user_input))

        rsp = await todo.run(prompt=prompt)
        msg = Message(content=rsp, role=self.profile, cause_by=todo)

        self.rc.memory.add(
            Message(f'\\[Prompt] {user_input} \\[/prompt]\n\\[Answer] {rsp} \\[/Answer]\n',
                    role=self.profile,
                    cause_by=todo)
        )

        return msg

    def get_chat_history(self, k=20):
        context = self.get_memories(k=k)
        return '\n'.join(c.content for c in context)


class SuperviseAction(BaseDynamicAction):
    name: str = "Supervise"

    async def run(self, **kwargs):
        pretext = 'In the following section you will be given a chat history, a prompt and an answer to the prompt by ' \
                  f'an AI ChatBot.\nDECIDE WHETHER THE ANSWER IS CORRECT AND APPROPRIATE OR NOT.\n' \
                  'UNDER ALL CIRCUMSTANCES ANSWER WITH THE FOLLOWING JSON:\n' \
                  '{"correct": true or false, "reason": "The answer is incorrect and inappropriate because ..."}\n' \
                  'If the answer is correct and appropriate, set "correct" to true and "reason" to an empty string.\n' \
                  'If the answer is incorrect and inappropriate, set "correct" to false and "reason" to a string' \
                  'explaining why.\n\nThe chat history, prompt and answer are as follows:\n\n'

        prompt = f'{pretext}\n##CHAT HISTORY: ' \
                 f'\n{kwargs.get("chat_history")}' \
                 f'\n\n##PROMPT: \n{kwargs.get("prompt")}' \
                 f'\n\n##ANSWER: \n{kwargs.get("answer")}\n\n'

        rsp = await self._aask(prompt)

        return rsp


class SuperviseVoteAction(BaseDynamicAction):
    name: str = "SuperviseVote"

    async def run(self, **kwargs):
        answers = '\n\n'.join('ANSWER ' + str(i) + ':\n' + response
                              for i, response in enumerate(kwargs.get("responses"))) + '\n\n'
        prompt = ('In the following section you will be given a prompt and multiple answers to the prompt by ' \
                  'AI ChatBots.\nPlease decide as to which answer is the best and most appropriate.\n' \
                  f'Under all circumstances answer with the following JSON:\n' \
                  '{"chosen": index}\nChange index to the index of the best answer.\n' \
                  'UNDER NO CIRCUMSTANCES ANSWER IN ANY DIFFERENT WAY OR ADD ANY ADDITIONAL TEXT\n\n' \
                  f'The original Prompt is as follows:\n{kwargs.get("prompt")}\n\n' \
                  f'The answers are as follows:\n\n' + answers)
        rsp = await self._aask(prompt)
        return rsp


class SupervisorRole(BaseRole):
    """
    Supervisor role
    """

    def __init__(self):
        super().__init__(actions=[SuperviseAction, SuperviseVoteAction])

    async def run(self, *args, **kwargs) -> Message:
        self.rc.todo = self.actions[0]
        rsp = await self._act(prompt=kwargs.get('prompt'), chat_history=kwargs.get('chat_history'),
                              answer=kwargs.get('answer'))
        try:
            rsp.content = json.loads(rsp.content)
        except json.JSONDecodeError:
            rsp.content = {"correct": False, "reason": "Supervisor failed"}
        return rsp

    async def vote(self, prompt: str, responses: list[str]) -> Message:
        """
        Cast a vote upon the best response for the given prompt

        :param prompt: The prompt for the responses
        :param responses: responses to vote on
        :return: the voted response (json)
        """
        self.rc.todo = self.actions[1]
        rsp = await self._act(prompt=prompt, responses=responses)

        try:
            rsp.content = json.loads(rsp.content)
            if not isinstance(rsp.content.get('chosen'), int):
                print('[bold orange]no answer chosen[/]')
                raise ValueError("No answer chosen")
        except (json.JSONDecodeError, ValueError):
            print(f'[bold red]invalid feedback from supervisor[/]')
            rsp.content = {"chosen": -1}
        return rsp

    async def _act(self, *args, **kwargs) -> Message:
        todo = self.rc.todo

        rsp = await todo.run(*args, **kwargs)
        msg = Message(content=rsp, role=self.profile, cause_by=todo)

        return msg


class Team:
    def __init__(self, agents: list[ChatRole] | tuple[ChatRole],
                 supervisors: list[SupervisorRole] | tuple[SupervisorRole],
                 history: list[tuple[str, str]] = None):
        self.agents = agents
        self.supervisors = supervisors
        self._history = history or list()

    @property
    def history(self):
        return self._history

    @history.setter
    def history(self, history) -> None:
        """
        Overwrite the chat history

        :param history: new chat history
        :return: none
        """
        for agent in self.agents:
            agent.set_history(history)

    async def __supervisors_run(self, prompt, answer, chat_history) -> list[dict]:
        """
        Run all supervisors in team on the given prompt

        :param prompt: Prompt that answer was generated for
        :param answer: Answer generated by the agent
        :param chat_history: Chat history
        :return: supervisor feedbacks
        """
        feedbacks: list[dict] = list()
        for supervisor in self.supervisors:
            feedbacks.append((await supervisor.run(prompt=prompt, answer=answer, chat_history=chat_history)).content)

        return feedbacks

    @staticmethod
    async def __supervised_run(prompt: str, feedbacks: list[dict], agent: ChatRole) -> str:
        """
        Rerun agent with feedback from supervisor.

        :param prompt: the original prompt
        :param feedbacks: feedbacks from the supervisors
        :param agent: agent to rerun
        :return: agent response
        """
        feedback_prompt = f'A supervisor has concluded that your previous prompt did not match the requirements of ' \
                          f'the prompt \'{prompt}\' for the following reasons: \n' + \
                          '\n'.join(feedback.get("reason") for feedback in feedbacks) + \
                          f'\nProvide a new better answer to following prompt: \n{prompt}\n' \
                          f'DO NOT APOLOGIZE FOR YOUR PREVIOUS ANSWER\n'

        response = (await agent.run(prompt=feedback_prompt)).content
        return response

    async def __supervised_run_all(self, prompt: str, response_feedbacks: list[list[dict]]) -> list[str]:
        """
        Run all agents in the team with the feedbacks from the supervisors and get the responses

        :param prompt: the original prompt
        :param response_feedbacks: list of feedbacks for each response
        :return: list of new responses
        """
        responses: list[str] = list()
        for feedbacks, agent in zip(response_feedbacks, self.agents):
            responses.append(await Team.__supervised_run(prompt, feedbacks, agent))

        return responses

    async def __supervisor_judge(self, prompt: str, responses: list[str]) -> list[list[dict]]:
        """
        Creates new feedback for each response

        :param prompt: the original prompt
        :param responses: list of responses generated by the agents
        :return: list of feedbacks
        """
        response_feedbacks: list[list[dict]] = list()
        for i, (response, agent) in enumerate(zip(responses, self.agents)):
            feedbacks = await self.__supervisors_run(prompt=prompt, answer=response,
                                                     chat_history=agent.get_chat_history())
            response_feedbacks.append(feedbacks)
        return response_feedbacks

    async def __supervisor_vote(self, prompt: str, responses: list[str]) -> str:
        """
        If multiple responses are agreed upon by all supervisors, let the supervisors vote on the best response

        :param prompt: the original prompt
        :param responses: list of responses up for vote
        :return: the voted response
        """
        # gather votes
        votes: list[int] = list()
        for supervisor in self.supervisors:
            votes.append((await supervisor.vote(prompt, responses)).content.get('chosen'))

        # get response with most votes
        # if it's a tie, a random one will be chosen
        winner: int = max(set(votes), key=votes.count)
        return responses[winner]

    @staticmethod
    async def __check_response_feedbacks(responses: list[str], response_feedbacks: list[list[dict]]) -> list[str]:
        """
        Checks the feedback on all responses and returns the first one which all supervisors agree is correct

        :param responses: list of responses
        :param response_feedbacks: list of feedbacks for each response
        :return: list of correct responses
        """
        correct_responses: list[str] = list()
        for response, feedbacks in zip(responses, response_feedbacks):
            if all(feedback.get('correct') for feedback in feedbacks):
                correct_responses.append(response)
        return correct_responses

    async def __run(self, prompt) -> str:
        """
            Generate output for the prompt

            :param prompt: Prompt to generate output for
            :return: str
            """
        # gather initial responses
        responses: list[str] = list()
        print('[bold cyan] Generate initial responses for prompt [/]')
        for i, agent in enumerate(self.agents):
            responses.append((await agent.run(prompt=prompt)).content)
            print(f'> {i + 1}/{len(self.agents)}')

        # gather feedbacks
        print(f'[bold cyan] Generate initial feedback for responses [/]')
        response_feedbacks: list[list[dict]] = await self.__supervisor_judge(prompt, responses)

        # iterate over and over until we get a correct response
        print(f'[bold cyan]Iterating over responses using supervisors if needed[/]')
        max_iter = 6
        i = 0
        while not (correct_responses := await Team.__check_response_feedbacks(responses, response_feedbacks)) and i < max_iter:
            print(f'Current Iteration: {i}')
            i += 1
            responses = await self.__supervised_run_all(prompt, response_feedbacks)
            if i < max_iter:
                response_feedbacks = await self.__supervisor_judge(prompt, responses)
            else:
                correct_responses = responses
        print(f'[bold green]Correct responses have been generated[/]')

        # if there is more than one agreed upon response, let the supervisors vote
        if len(correct_responses) > 1:
            print(f'[bold cyan]Supervisors voting on best response[/]')
            return await self.__supervisor_vote(prompt, correct_responses)

        return correct_responses[0]

    async def __call__(self, prompt) -> str:
        self.history.append(('User', prompt))
        response = await self.__run(prompt)
        self.history.append(('Bot', response))
        return response

    def __repr__(self):
        return f'<Team: agents={len(self.agents)}, supervisors={len(self.supervisors)}>'