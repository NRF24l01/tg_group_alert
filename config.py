from dotenv import load_dotenv
from os import getenv
from json import loads

load_dotenv()

TOKEN = getenv("TOKEN")
ADMINS = loads(getenv("ADMINS"))