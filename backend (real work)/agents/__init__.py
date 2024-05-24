import asyncio

from metagpt.context import Context
from metagpt.roles.product_manager import ProductManager
from metagpt.logs import logger


async def main():
    msg = "Write a PRD for a tetris game"
    context = Context()  # The session Context object is explicitly created, and the Role object implicitly shares it automatically with its own Action object
    role = ProductManager(context=context)
    while msg:
        msg = await role.run(msg)
        logger.info(str(msg))

if __name__ == '__main__':
    asyncio.run(main())
