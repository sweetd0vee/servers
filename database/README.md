# Интеграция с базой данных

## Обзор

Проект использует PostgreSQL в качестве основного хранилища данных для метрик серверов.
Интеграция реализована через SQLAlchemy ORM для единообразной работы с базой данных.

## Структура модулей

```
database/
├── __init__.py          # Инициализация пакета
├── connection.py        # Подключение к БД (SQLAlchemy)
├── table.py            # Модели данных (ServerMetrics)
├── repository.py       # Репозиторий для работы с данными
├── init_database.py    # Скрипт инициализации БД
├── migrate_excel_to_db.py  # Миграция данных из Excel
├── db_import.py        # Импорт данных (legacy, psycopg2)
└── db_export.py       # Экспорт данных (legacy, psycopg2)
```

## Быстрый старт

### 1. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
DB_HOST=postgres
DB_PORT=5432
DB_NAME=server_monitoring
DB_USER=postgres
DB_PASSWORD=your_password
```

### 2. Инициализация базы данных

```bash
# Создание таблиц
python database/init_database.py
```

### 3. Миграция данных из Excel

```bash
# Проверка данных (dry-run)
python database/migrate_excel_to_db.py data/metrics.xlsx --dry-run

# Миграция данных
python database/migrate_excel_to_db.py data/metrics.xlsx

# С инициализацией БД
python database/migrate_excel_to_db.py data/metrics.xlsx --init-db
```

## Использование в коде

### Базовое использование

```python
from database.repository import MetricsRepository, get_metrics_from_db
import pandas as pd

# Простой способ (создает и закрывает сессию автоматически)
df = get_metrics_from_db()

# С фильтрами
df = get_metrics_from_db(
    vm='server-01',
    start_date=date(2025, 1, 1),
    end_date=date(2025, 1, 31)
)
```

### Использование репозитория

```python
from database.repository import MetricsRepository
from datetime import date

# С контекстным менеджером (рекомендуется)
with MetricsRepository() as repo:
    # Получить все метрики
    df = repo.get_all_metrics()
    
    # Получить метрики сервера
    df = repo.get_metrics_by_server('server-01')
    
    # Получить метрики за период
    df = repo.get_metrics_by_date_range(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31)
    )
    
    # Получить список серверов
    servers = repo.get_unique_servers()
    
    # Получить сводку по серверу
    summary = repo.get_server_summary('server-01')
    
    # Вставить метрику
    repo.insert_metric(
        vm='server-01',
        date=date(2025, 1, 15),
        metric='cpu.usage.average',
        avg_value=45.5
    )
    
    # Массовая вставка
    result = repo.insert_from_dataframe(df)
    print(f"Вставлено: {result['success']}, ошибок: {result['errors']}")
```

## Модель данных

### Таблица: server_metrics

| Колонка | Тип | Описание |
|---------|-----|----------|
| id | UUID | Первичный ключ |
| vm | VARCHAR(255) | Имя сервера |
| date | TIMESTAMP | Дата метрики |
| metric | VARCHAR(100) | Название метрики |
| max_value | DECIMAL(10,5) | Максимальное значение |
| min_value | DECIMAL(10,5) | Минимальное значение |
| avg_value | DECIMAL(10,5) | Среднее значение |
| created_at | TIMESTAMP | Дата создания |
| updated_at | TIMESTAMP | Дата обновления |

### Индексы

- `idx_metrics_vm_date` - на (vm, date, metric)
- `idx_metrics_date` - на date
- `idx_metrics_metric` - на metric
- `uq_vm_date_metric` - уникальный индекс на (vm, date, metric)

## API репозитория

### Методы получения данных

- `get_all_metrics()` - получить все метрики с фильтрацией
- `get_metrics_by_server(vm)` - метрики конкретного сервера
- `get_metrics_by_date_range(start_date, end_date, vm=None)` - метрики за период
- `get_unique_servers()` - список уникальных серверов
- `get_unique_metrics()` - список уникальных метрик
- `get_date_range()` - диапазон дат в БД
- `get_server_summary(vm)` - сводка по серверу

### Методы вставки данных

- `insert_metric(vm, date, metric, max_value, min_value, avg_value)` - вставить одну метрику
- `insert_from_dataframe(df)` - массовая вставка из DataFrame

### Методы управления

- `delete_old_metrics(days=90)` - удалить старые метрики

## Интеграция в приложение

В `app/app_new.py` функция `load_and_prepare_data()` теперь поддерживает оба источника:

```python
# Из базы данных (по умолчанию)
df = load_and_prepare_data(data_source='db')

# Из Excel файла (legacy)
df = load_and_prepare_data(data_source='xlsx')
```

Администраторы могут переключать источник данных через интерфейс.

## Обработка ошибок

Репозиторий автоматически обрабатывает ошибки и логирует их:

```python
try:
    with MetricsRepository() as repo:
        df = repo.get_all_metrics()
except Exception as e:
    logger.error(f"Ошибка работы с БД: {e}")
    # Fallback на Excel или показ ошибки пользователю
```

## Производительность

- Используется connection pooling (SQLAlchemy)
- Кэширование запросов через `@st.cache_data` (TTL 5 минут)
- Индексы для быстрого поиска
- Batch вставка для массовых операций

## Миграция с Excel на БД

1. **Инициализируйте БД:**
   ```bash
   python database/init_database.py
   ```

2. **Импортируйте данные:**
   ```bash
   python database/migrate_excel_to_db.py data/metrics.xlsx
   ```

3. **Проверьте данные:**
   ```python
   from database.repository import get_metrics_from_db
   df = get_metrics_from_db()
   print(f"Записей в БД: {len(df)}")
   ```

4. **Обновите приложение:**
   - По умолчанию используется `data_source='db'`
   - Excel остается как fallback

## Troubleshooting

### Ошибка подключения

```
❌ Ошибка подключения к базе данных
```

**Решение:**
1. Проверьте переменные окружения
2. Убедитесь, что PostgreSQL запущен
3. Проверьте сеть Docker (если используется)

### Пустая база данных

```
⚠️ База данных пуста или недоступна
```

**Решение:**
1. Импортируйте данные: `python database/migrate_excel_to_db.py data/metrics.xlsx`
2. Или используйте Excel как источник данных

### Ошибка при вставке

```
⚠️ Ошибок при вставке: X
```

**Решение:**
1. Проверьте формат данных в Excel
2. Убедитесь, что все обязательные колонки присутствуют
3. Проверьте логи для деталей

## Дальнейшее развитие

- [ ] Миграции через Alembic
- [ ] Партиционирование таблиц по датам
- [ ] Автоматическая очистка старых данных
- [ ] Репликация для высокой доступности
- [ ] Архивация данных

