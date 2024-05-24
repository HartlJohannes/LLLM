import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from configurations import Configuration

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

@app.get("/cfg/{uid}")
def

@app.post("/cfg/pluck")
def pluck_config


if __name__ == "__main__":
    # run app (duh!)
    uvicorn.run(app, host="0.0.0.0", port=8080)
