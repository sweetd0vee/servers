"""
Скрипт для инициализации базы данных
Создает таблицы и индексы
"""
from database.connection import Base, engine, DATABASE_URL
from database.models import ServerMetrics
from base_logger import logger
import sys


def init_database():
    """
    Инициализация базы данных - создание всех таблиц

    Returns:
        True если успешно, False в противном случае
    """
    try:
        logger.info("Создание таблиц в базе данных...")
        logger.info(f"База данных: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

        # Создаем все таблицы
        Base.metadata.create_all(bind=engine)

        logger.info("Таблицы созданы успешно!")
        logger.info(f"   - Таблица: {ServerMetrics.__tablename__}")
        logger.info(f"   - Индексы: idx_metrics_vm_date, idx_metrics_date, idx_metrics_metric")

        return True

    except Exception as e:
        logger.error(f"Ошибка при создании таблиц: {e}", exc_info=True)
        return False


def check_database_connection():
    """
    Проверка подключения к базе данных

    Returns:
        True если подключение успешно, False в противном случае
    """
    try:
        from database.connection import engine
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()
        logger.info("Подключение к базе данных успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return False


def main():
    """Основная функция"""
    print("=" * 60)
    print("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ СЕРВЕРНОГО МОНИТОРИНГА")
    print("=" * 60)
    print()

    # Проверяем подключение
    if not check_database_connection():
        print("Не удалось подключиться к базе данных")
        print("Проверьте настройки подключения в переменных окружения:")
        print("  - DB_HOST")
        print("  - DB_PORT")
        print("  - DB_NAME")
        print("  - DB_USER")
        print("  - DB_PASSWORD")
        sys.exit(1)

    # Создаем таблицы
    if not init_database():
        print("Не удалось создать таблицы")
        sys.exit(1)

    print()
    print("=" * 60)
    print("Инициализация завершена успешно!")
    print("=" * 60)
    print()
    print("Следующие шаги:")
    print("1. Импортируйте данные из Excel используя database/migrate_excel_to_db.py")
    print("2. Или используйте функцию импорта в интерфейсе приложения")


if __name__ == "__main__":
    main()

