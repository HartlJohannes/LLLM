import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
import requests
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime
from rich import print
import json

THIS_DIR = Path(__file__).parent
API_BASE = 'http://212.132.116.206:3000'

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Error:
    def __init__(self, raw: str, type: str, reason: str, recommended_fix: str, timestamp: str):
        self.raw: str = raw
        self.type: str = type
        self.reason: str = reason
        self.recommended_fix: str = recommended_fix
        self.timestamp = timestamp


# this should at some point be replaced with a proper database
errors: list[Error] = list()


def process_json_prompt(prompt: str, iteration: int = 0):
    print('[bold cyan]Sending prompt to Lumin API[/]')
    response = requests.post(
        f'{API_BASE}/nosession/send-with-context?prompt={requests.utils.quote(prompt)}'
    ).text[1:-1].replace('\\n', '').replace('\\', '').strip()
    print(f'[bold cyan]Received response from Lumin API:[/]\n{response}')
    response = response.replace('\\', '')
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        if iteration > 5:
            print('[bold red]Error: Could not parse JSON response - aborting![/]')
            return
        print('[bold red]Error: Could not parse JSON response - retrying![/]')
        return process_json_prompt(prompt, iteration + 1)
    return data


@app.post('/wtf')
def wtf(prompt: str):
    prompt = 'The Advanced Robotics Command Language (ARCL) is a text-based language used for integrating a fleet of ' \
             'adept mobile robots with an external automation system.\n' \
             'Interpret the following error ARCL error message.\n' \
             'The most important thing is, that your answer is allways in JSON FORMAT ' \
             'and that is follows the FOLLOWING FORMAT: {"type": "error_type", "reason": "error_reason", "recommended_fix": "fix"} !\n' \
             'Set error_type to the type of error (sucha as CommandError, RouteError, SetUpError, ...), reason to the reason the error was raised for and recommended_fix to a recommendation on how to fix the issue.\n' \
             f'The error message you should interpret is is: \n{prompt}\n'
    return process_json_prompt(prompt)


@app.post('/log')
def log():
    response = errors
    return response[::-1]


@app.post('/log/add')
def log_error(raw: str):
    now = datetime.now()

    data = wtf(raw)
    error = Error(raw, data.get('type'), data.get('reason'), data.get('recommended_fix'),
                  timestamp=now.strftime("%m/%d/%Y, %H:%M:%S"))
    errors.append(error)
    return {'status': 'success'}

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
