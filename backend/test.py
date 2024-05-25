from agents.agents import ChatRole, SupervisorRole
import asyncio
from agents import Team
from metagpt.logs import logger
from argparse import ArgumentParser
from rich import print


async def test_chatbot():
    """
    Test the chatbot
    """
    print('[bold green]Starting chatbot test[/]')

    bots = ChatRole(), ChatRole(), ChatRole()
    supervisors = SupervisorRole(), SupervisorRole()
    team = Team(bots, supervisors)

    while print('[bold green]+++ [/]', end='') or (prompt:=input('')):
        print(f'[green]{await team(prompt)}[/]')


async def test_vector():
    """
    Test the vector database integration
    """
    print('[bold green]Starting vector test[/]')
    try:
        import rag
    except Exception as e:
        print(f'[bold red]Error: {e}[/]')
        return
    print('[bold green]Vector test complete[/]')


if __name__ == '__main__':
    parser = ArgumentParser(
        prog='Lumin',
        description='Lumin API server testing script',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode',
    )
    parser.add_argument(
        '--chatbot',
        action='store_true',
        help='Test the chatbot',
    )
    parser.add_argument(
        '--vector',
        action='store_true',
        help='Test the vector database integration',
    )
    args = parser.parse_args()

    if not args.debug:
        logger.stop()

    if args.chatbot:
        asyncio.run(test_chatbot())

    if args.vector:
        asyncio.run(test_vector())
