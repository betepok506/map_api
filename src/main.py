import uvicorn
from fastapi import FastAPI, Response
from fastapi_health import health
import os
import logging
import requests
import time
import tenacity
from tenacity import *
from src.mbtiles import MbtileSet
from src.logger import LoggerFormating
from src.server_api import ServerAPI, query_to_server
from src.utils import md5

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(LoggerFormating())
logger.addHandler(handler)
logger.propagate = False

app = FastAPI()
tileset = None
MAP_NAME = os.getenv("MAP_NAME")
SERVER_URL = os.getenv("SERVER_URL")
CNT_TILE = 500  # максимальное количество tiles для одновременной отправки
server_api = ServerAPI(server_url=SERVER_URL, map_name=MAP_NAME)

BEGIN_RECONNECT_TIME = 5
STEP_RECONNECT_TIME = 5
MAX_RECONNECT_TIME = 30


@app.on_event('startup')
def load_mbtiles():
    global tileset
    FILE_NAME_MBTILES = os.path.join("./data", os.getenv("FILE_NAME_MBTILES"))
    logger.info(f'Path loading Mbtiles: {FILE_NAME_MBTILES}.')

    tileset = MbtileSet(mbtiles=FILE_NAME_MBTILES)
    hash_md5 = md5(FILE_NAME_MBTILES)

    response_json = query_to_server(server_api.URL_REQUEST_MAP_CACHE_DATABASE)
    # TODO: Сравнить полученный хеш с базы и хеш локальный
    # Если запрос пустой создать карту и добавить tiles
    # Если они равны все норм, выходим
    # Если хеш не равен, удаляем tiles, удаляем хеш, добавляем все в базу

    if response_json != {} and hash_md5 == response_json["hash_md5"]:
        # Если они равны все норм, выходим
        return

    if response_json != {} and hash_md5 != response_json["hash_md5"]:
        response_json = query_to_server(server_api.URL_DELETING_MAP_TO_DATABASE,
                                        data={
                                            "map_name": MAP_NAME,
                                            "hash_md5": hash_md5
                                        })
        logger.info(f"{response_json}")
    # Добавление карты в базу данных
    response_json = query_to_server(server_api.URL_ADDING_MAP_TO_DATABASE,
                                    data={
                                        "map_name": MAP_NAME,
                                        "hash_md5": hash_md5
                                    })

    cur_hash_md5, map_id = response_json["hash_md5"], response_json["map_id"]
    update_tiles_in_db(MAP_NAME, cur_hash_md5)

    tiles = []
    for tile in tileset.get_all_tiles():
        if len(tiles) < CNT_TILE:
            tiles.append({"map_id": map_id,
                          "x": tile.col,
                          "y": tile.row,
                          "z": tile.zoom})

        if len(tiles) == CNT_TILE:
            response = requests.post(f'http://{SERVER_URL}/add_tiles/', json={
                "tiles": tiles
            })

            if response.status_code != 200:
                # TODO: Механизм повторной отправки tiles
                logger.warning(f"Error loading tile x: {tile.col}, y: {tile.row}, zoom: {tile.zoom}")

            tiles.clear()

    logger.info(f'Loading successfully')


# @retry(wait=wait_fixed(2), retry=retry_if_exception_type(requests.exceptions.ConnectionError))
# def query_hash_md5_map(url: str):
#     """
#     Функция запроса хеша карты
#
#     Parameters:
#     ------------
#     url: `str`
#         URL - адрес запроса хеша, хранящегося в базе сервера
#
#     Returns
#     ------------
#     `json`
#         Ответ сервера, содержащий хеш карты, хранящийся на сервере
#     """
#     try:
#         response = requests.get(url)
#     except requests.exceptions.ConnectionError as connection_error:
#         logger.warning(
#             f"Failed to connect to the server, check if the URL is specified correctly."
#             f"\n\tExceprions: {connection_error}."
#             f" \n\tRetrying..."
#         )
#         raise connection_error
#
#     if response.status_code == 200:
#         return response.json()
#
#     logger.warning(f"The server returned an incorrect response.  Retrying...")
#     # TODO: Выдавать другую ошибку
#     raise requests.exceptions.ConnectionError(
#         f"The server returned an incorrect response. Retry"
#     )


# @retry(wait=wait_fixed(2))
# def query_hash_md5_map(url: str, max_retry: int = 5):
#     """
#
#     Parameters:
#     ------------
#     :param url:
#     :param max_retry:
#
#     Returns
#     ------------
#     """
#     cur_reconnect_time = BEGIN_RECONNECT_TIME
#     cnt_retry = 0
#
#     while True:
#         response = requests.get(url)
#         if response.status_code == 200:
#             break
#
#         logger.warning(
#             f"Failed to connect to the server, check if the URL is specified correctly. "
#             f"Retry after {cur_reconnect_time} seconds."
#         )
#         time.sleep(cur_reconnect_time)
#         cur_reconnect_time = min(MAX_RECONNECT_TIME, cur_reconnect_time + STEP_RECONNECT_TIME)
#         cnt_retry += 1
#         if cnt_retry != -1 and cnt_retry > max_retry:
#             raise "Failed to connect to the server, check if the URL is specified correctly"
#
#     return response.json()


def add_map(url: str, json_data: dict, max_retry: int = 5):
    """
    Функция добавления карты в БД

    Parameters
    -----------
    :param url:
    :param json_data:
    :param max_retry:

    Returns
    -----------

    """

    cur_reconnect_time = BEGIN_RECONNECT_TIME
    cnt_retry = 0
    while True:
        response = requests.post(url, json=json_data)
        if response.status_code == 200:
            break

        logger.warning(f"Failed to add map data to the database. Check the correctness "
                       f"of the environment variable - SERVER_URL. Retry after {cur_reconnect_time} seconds.")

        time.sleep(cur_reconnect_time)
        cur_reconnect_time = min(MAX_RECONNECT_TIME, cur_reconnect_time + STEP_RECONNECT_TIME)
        cnt_retry += 1
        if cnt_retry != -1 and cnt_retry > max_retry:
            raise "Failed to add map data to the database. Check the correctness " \
                  "of the environment variable - SERVER_URL."

    return response.json()


def update_tiles_in_db(map_name: str, hash_md5: str):
    """Функция для удаления предыдущи tiles карты с текущим названием"""
    pass


@app.get("/google_map/",
         response_class=Response,
         responses={
             200: {
                 "content": {"application/octet-stream": {}}
             }
         }
         )
async def root(z: int, x: int, y: int):
    tile = tileset.get_tile(z, x, y)
    return Response(
        content=tile.get_png(),
        media_type="application/octet-stream",
    )


def check_ready():
    return tileset is not None


async def success_handler(**kwargs):
    return Response(status_code=200, content='Mbtiles is loaded')


async def failure_handler(**kwargs):
    return Response(status_code=500, content='Mbtiles is not loaded')


app.add_api_route('/health', health([check_ready],
                                    success_handler=success_handler,
                                    failure_handler=failure_handler))

if __name__ == "__main__":
    uvicorn.run("main:app", port=8282, log_level="info", reload=True)
