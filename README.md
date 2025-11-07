# Backend для работы с интервью и бизнес-требованиями

## Стек технологий

- **Python 3.13**
- **UV** - пакетный менеджер
- **FastAPI** - фраймворк
- **Alembic** — миграции базы данных
- **SQLAlchemy** — ORM
- **PostgreSQL** — база данных
- **Docker / Docker Compose** — контейнеризация
- **pydantic** — для конфигураций и валидаций

## Структура проекта

```plaintext
.
├── app/
│   ├── api/                 # роутеры
│   ├── core/                # конфигурации и настройки
│   ├── cruds/               # круд операции
│   ├── dependencies/        # зависимости
│   ├── exceptions/          # обработка ошибок
│   ├── models/              # ORM модели
│   ├── schemas/             # схемы pydantic
│   ├── services/            # сервисы
│   └── main.py              # точка входа приложения
```
## Команды для работы

### Установка зависимостей
```bash
uv add requests
```

### Создание и применение миграций
```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

### Запуск проекта через Docker
```bash
docker-compose up -d
```
При успешном билде можно открыть Swagger:
[http://localhost:8080/docs](http://localhost:8080/docs)

