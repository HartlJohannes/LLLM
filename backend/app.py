import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from configurations import Configuration
from agents import sessions
from pathlib import Path
from argparse import ArgumentParser
import asyncio

THIS_DIR = Path(__file__).parent


app = FastAPI()

@app.get("/status")
async def status():
    return {"status": "up"}


@app.get('/', response_class=HTMLResponse)
async def root():
    with open(f'{THIS_DIR}/html_templates/landing.html', 'r') as f:
        return f.read()


class WebConfiguration(BaseModel):
    agent_count: int
    supervisor_count: int


@app.post("/cfg/register/")
async def register_config(configuration: WebConfiguration):
    """
    Register a new configuration. If successful returns the uid of the configuration otherwise returns an error.

    :param configuration: The configuration to register
    :return: uid of the configuration or error
    """
    try:
        cfg = Configuration(agent_count=configuration.agent_count, supervisor_count=configuration.supervisor_count)
        cfg.save()
        return {"uid": cfg.uid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@app.post("/cfg/pluck")
async def pluck_config(uid: int):
    """
    Pluck a configuration from the database

    :param uid: uid of the configuration
    :return: the configuration if found else 404
    """
    cfg = Configuration.grab(uid)
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return {
        "agent_count": cfg.agent_count,
        "supervisor_count": cfg.supervisor_count,
        "uid": cfg.uid,
    }


@app.post("/session/create")
async def create_session(config_uid: int):
    """
    Create a new session

    :param config_uid: UID of the configuration which should be used for the session
    :return: session key
    """
    session = sessions.Session(config_uid)
    session.save()
    sessions.Cache.add(session)
    return {'session_key': session.key}


@app.post("/session/read")
async def read_session(session_key: str):
    """
    Reopen a previous session (read conversation data)

    :param session_key: session key
    :return: list of messages
    """
    session = sessions.Cache.locate(session_key)
    if not session:
        return HTTPException(status_code=400, detail='session not found')
    return await session.history()

@app.post("/session/send")
async def send_session(session_key: str, prompt: str):
    """
    Send a message to team in a session

    :param session_key: session key
    :param prompt: message
    :return: response from session team
    """
    session = sessions.Cache.locate(session_key)
    if not session:
        return HTTPException(status_code=400, detail="session not found")
    return await session.send(prompt)


@app.post("/nosession/send")
async def send_nosession(prompt: str):
    """
    Send a message to a team without a session

    :param prompt: message
    :return: response from team
    """
    team = sessions.Team(agents=[sessions.ChatRole()], supervisors=[sessions.SupervisorRole()])
    return await team(prompt)


@app.get("/cfg/{uid}")
async def alt_pluck_config(uid: int):
    """
    Shortcut for /cfg/pluck

    :param uid: UID of the configuration
    :return: the configuration if found else 404
    """
    return await pluck_config(uid)


@app.post("/session/open")
async def open_session(session_key: str):
    """
    Reopen a session and get metadata about it.

    :param session_key: session key
    :return: session details
    """
    if not sessions.Cache.check(session_key):
        session = sessions.Session.find(session_key)
        if not session:
            return HTTPException(status_code=404, detail="Configuration not found")
        sessions.Cache.add(session)
    else:
        session = sessions.Cache.find(session_key)

    cfg = session.config
    return {
        "uid": session.uid,
        "session_key": session.key,
        "supervisor_count": cfg.supervisor_count,
        "agent_count": cfg.agent_count
    }


@app.get("/session/list")
async def list_sessions():
    """
    Retrieve list of all session keys

    :return: session keys
    """
    return sessions.Session.list()


if __name__ == "__main__":
    parser = ArgumentParser(
        prog='Lumin',
        description="Lumin API server",
        epilog="Lumin API server help"
    )
    parser.add_argument('-p', '--port', default=3000, type=int, dest='port')
    args = parser.parse_args()

    # run app (duh!)
    uvicorn.run(app, host="0.0.0.0", port=args.port)
