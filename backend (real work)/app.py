import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from configurations import Configuration
from agents import sessions

app = FastAPI()


@app.get("/status")
def read_root():
    return {"status": "up"}


class WebConfiguration(BaseModel):
    agent_count: int
    supervisor_count: int


@app.post("/cfg/register/")
def register_config(configuration: WebConfiguration):
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
def pluck_config(uid: int):
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
def create_session(config_uid: int):
    """
    Create a new session

    :param config_uid: UID of the configuration which should be used for the session
    :return: session key
    """
    session = sessions.Session(config_uid)
    session.save()
    return {'session_key': session.key}

@app.post("/session/read")
def open_session(session_key: str):
    """
    Reopen a previous session (read metadata)

    :param session_key: session key
    :return: session id
    """
    return {"session_id": 1}


@app.post("/session/read")
def read_session(session_key: str):
    """
    Reopen a previous session (read conversation data)

    :param session_key: session key
    :return: list of messages
    """
    return [
        ('User', 'Hello'),
        ('Bot', 'Hi there!'),
        ('User', 'How are you?'),
        ('Bot', 'I am good, thank you!'),
    ]


@app.get("/cfg/{uid}")
def alt_pluck_config(uid: int):
    """
    Shortcut for /cfg/pluck

    :param uid: UID of the configuration
    :return: the configuration if found else 404
    """
    return pluck_config(uid)


@app.post("/session/open")
def open_session(session_key: str):
    """
    Open a new session

    :param session_key: session key
    :return: whether the session was opened/(found)
    """
    return {"status": "opened"}


if __name__ == "__main__":
    session = sessions.Session.find('0893ce8c-7369-474a-9086-d1a3af8db5ee')
    print(session)
    print({'session_key': session.key})
    # run app (duh!)
    uvicorn.run(app, host="0.0.0.0")#, port=8080)