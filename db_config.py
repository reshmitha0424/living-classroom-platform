import os

from dotenv import load_dotenv


load_dotenv()

BIRDWEATHER_AUTH_KEY = os.environ["BIRDWEATHER_AUTH_KEY"]
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ["DB_PORT"])
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
