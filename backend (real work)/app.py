import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/status")
def read_root():
    return {"status": "up"}


if __name__ == "__main__":
    # run app (duh!)
    uvicorn.run(app, host="0.0.0.0", port=8080)