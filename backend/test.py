from agents.agents import ChatRole, SupervisorRole
import asyncio
from agents import Team
from metagpt.logs import logger

if __name__ == '__main__':
    from metagpt.context import Context
    from rich import print

    logger.stop()

    # do some testing
    async def main():
        bots = ChatRole(), ChatRole(), ChatRole()
        supervisors = SupervisorRole(), SupervisorRole()
        team = Team(bots, supervisors)

        while print('[bold green]+++ [/]', end='') or (prompt:=input('')):
            print(f'[green]{await team(prompt)}[/]')

    asyncio.run(main())
