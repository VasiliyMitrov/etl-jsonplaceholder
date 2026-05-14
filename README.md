# ETL: JSONPlaceholder → SQLite

Пайплайн загружает данные из публичного REST API [jsonplaceholder.typicode.com](https://jsonplaceholder.typicode.com/) — пользователи, посты, комментарии — и сохраняет в локальную SQLite-базу.

Повторный запуск безопасен: дублей не будет. При каждом запуске в логах видно сколько записей было до и стало после.

---

## Быстрый старт

```bash
git clone <repo_url>
cd etl-jsonplaceholder

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -e .
python -m etl
```

После запуска в текущей директории появится `data.db`.

---

## Структура проекта

```
.
├── src/etl/
│   ├── __main__.py   # точка входа, оркестрация пайплайна
│   ├── config.py     # настройки из переменных окружения
│   ├── fetcher.py    # HTTP-клиент с автоматическим retry
│   └── db.py         # схема БД и upsert-логика
├── tests/
│   └── test_etl.py   # unit и интеграционные тесты
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

---

## Запуск

### Базовый

```bash
python -m etl
```

### С указанием пути к БД

```bash
python -m etl --db /path/to/my.db
```

### Через переменные окружения

```bash
API_BASE_URL=https://jsonplaceholder.typicode.com \
DB_PATH=/data/prod.db \
REQUEST_TIMEOUT=60 \
python -m etl
```

---

## Конфигурация

| Переменная        | По умолчанию                           | Описание                   |
|-------------------|----------------------------------------|----------------------------|
| `API_BASE_URL`    | `https://jsonplaceholder.typicode.com` | Base URL API               |
| `DB_PATH`         | `data.db`                              | Путь к SQLite-файлу        |
| `REQUEST_TIMEOUT` | `30`                                   | Таймаут HTTP-запроса (сек) |

Аргумент `--db` имеет приоритет над переменной окружения `DB_PATH`.

---

## Схема базы данных

```
users
├── id        INTEGER  PK
├── name      TEXT
├── username  TEXT
├── email     TEXT
├── phone     TEXT
├── website   TEXT
├── company   TEXT     (название компании)
└── address   TEXT     (улица, город)

posts
├── id        INTEGER  PK
├── user_id   INTEGER  FK → users.id
├── title     TEXT
└── body      TEXT

comments
├── id        INTEGER  PK
├── post_id   INTEGER  FK → posts.id
├── name      TEXT
├── email     TEXT
└── body      TEXT
```

Типичный объём данных: 10 пользователей, 100 постов, 500 комментариев.

---

## Идемпотентность

Повторный запуск не создаёт дублей. Используется `INSERT ... ON CONFLICT(id) DO UPDATE SET` — при совпадении первичного ключа запись обновляется, а не дублируется.

Пример вывода при первом запуске:
```
2024-01-15 10:00:01 [INFO] Starting ETL pipeline → data.db
2024-01-15 10:00:01 [INFO] Fetched 10 records from /users
2024-01-15 10:00:01 [INFO] Fetched 100 records from /posts
2024-01-15 10:00:02 [INFO] Fetched 500 records from /comments
2024-01-15 10:00:02 [INFO] ETL complete. Summary:
2024-01-15 10:00:02 [INFO]   users       fetched=10   db_before=0    db_after=10
2024-01-15 10:00:02 [INFO]   posts       fetched=100  db_before=0    db_after=100
2024-01-15 10:00:02 [INFO]   comments    fetched=500  db_before=0    db_after=500
```

При повторном запуске `db_before` равен `db_after` — данные обновились, новых строк нет.

---

## Тесты

```bash
pip install -e ".[dev]"
pytest
```

С отчётом о покрытии:

```bash
pytest --cov=etl --cov-report=term-missing
```

Тесты не делают реальных HTTP-запросов — вместо обращения к API используются заглушки с фиксированными данными. Каждый тест работает с изолированной временной БД.

---

## Требования

- Python 3.10+
- `requests` 2.32+
- Для тестов: `pytest` 8.0+, `pytest-cov` 5.0+
