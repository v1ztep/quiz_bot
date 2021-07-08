import os
import redis
from dotenv import load_dotenv
load_dotenv()


def connect_to_redis_db():
    redis_host, redis_port = os.getenv('REDISLABS_ENDPOINT').split(':')
    redis_db_pass = os.getenv('REDIS_DB_PASS')
    redis_db = redis.Redis(host=redis_host,
                           port=redis_port,
                           db=0,
                           password=redis_db_pass,
                           decode_responses=True)
    return redis_db
