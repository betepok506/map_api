from fastapi import FastAPI, Response
from fastapi_health import health
import os
import logging
from src.mbtiles import MbtileSet
from src.logger import LoggerFormating


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(LoggerFormating())
logger.addHandler(handler)
logger.propagate = False

app = FastAPI()
tileset = None


@app.on_event('startup')
def load_mbtiles():
    global tileset
    FILE_NAME_MBTILES = os.path.join("./data", os.getenv("FILE_NAME_MBTILES"))
    logger.info(f'Path loading Mbtiles: {FILE_NAME_MBTILES}.')
    tileset = MbtileSet(mbtiles=FILE_NAME_MBTILES)
    logger.info(f'Loading successfully')


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
