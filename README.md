# Map API
### Описание

Данный проект представляет реализацию Map API на основе Fast APi. 
На данный момент работает только с форматом `MBtiles`. 
Решение упаковано в Docker-контейнер, команда запуска находится в разделе "Запуск".
Для работы `MBtiles` должен располагаться в каталоге `data`.


### Установка зависимостей
Для локального запуска необходимо воспользоваться командой:

```commandline
pip install -r requirements.txt
```

### Конфигурирование
Конфигурирование проекта осуществляется с помощью `.env`, файла расположенного в корневом каталоге
 - `PORT` --- Порт, по которому будет доступен API
 - `FILE_NAME_MBTILES` --- Имя MBtiles файла

### Запуск

Для запуска в Docker-контейнере необходимо воспользоваться командой:

```
bash tools/run.sh
```

Для локального запуска необходимо воспользоваться командой:
```commandline
source .env
uvicorn src.main:app --reload --workers 1 --host 0.0.0.0 --port 8000
```

### Использование API с Leaflet

Для работы с Leaflet в слое L.TileLayer необходимо указать URL: `http://localhost:<YOUR PORT>/google_map/?z={z}&x={x}&y={y}` 
и установить параметр `tsm` в значение `True`.

Исчерпывающий пример конфигурации:
```commandline
new L.TileLayer('http://localhost:8282/google_map/?z={z}&x={x}&y={y}', {
                    maxZoom: 24,
                    tms: true,
                     subdomains: ['mt0', 'mt1', 'mt2', 'mt3']
              })
```

