"""
Утилита для работы с миграциями базы данных через Alembic
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic.config import Config
from alembic import command
from database.connection import DATABASE_URL
from base_logger import logger


def get_alembic_config():
    """Получение конфигурации Alembic"""
    alembic_cfg = Config()
    alembic_cfg.set_main_option('script_location', 'database/migrations')
    alembic_cfg.set_main_option('sqlalchemy.url', DATABASE_URL)
    return alembic_cfg


def init_migrations():
    """Инициализация миграций (если еще не сделано)"""
    logger.info("Инициализация миграций...")
    # Миграции уже инициализированы, но можно добавить проверку
    logger.info("✅ Миграции готовы к использованию")


def create_migration(message: str, autogenerate: bool = True):
    """
    Создание новой миграции

    Args:
        message: Описание миграции
        autogenerate: Автоматически генерировать на основе моделей
    """
    logger.info(f"Создание миграции: {message}")
    alembic_cfg = get_alembic_config()

    try:
        if autogenerate:
            command.revision(alembic_cfg, autogenerate=True, message=message)
        else:
            command.revision(alembic_cfg, message=message)
        logger.info("Миграция создана успешно")
    except Exception as e:
        logger.error(f"Ошибка при создании миграции: {e}")
        raise


def upgrade(revision: str = "head"):
    """
    Применение миграций

    Args:
        revision: Версия для применения (по умолчанию 'head' - последняя)
    """
    logger.info(f"Применение миграций до версии: {revision}")
    alembic_cfg = get_alembic_config()

    try:
        command.upgrade(alembic_cfg, revision)
        logger.info("Миграции применены успешно")
    except Exception as e:
        logger.error(f"Ошибка при применении миграций: {e}")
        raise


def downgrade(revision: str = "-1"):
    """
    Откат миграций

    Args:
        revision: Версия для отката (по умолчанию '-1' - одна версия назад)
    """
    logger.info(f"Откат миграций до версии: {revision}")
    alembic_cfg = get_alembic_config()

    try:
        command.downgrade(alembic_cfg, revision)
        logger.info("Миграции откачены успешно")
    except Exception as e:
        logger.error(f"Ошибка при откате миграций: {e}")
        raise


def show_current():
    """Показать текущую версию БД"""
    alembic_cfg = get_alembic_config()
    try:
        command.current(alembic_cfg)
    except Exception as e:
        logger.error(f"Ошибка: {e}")


def show_history():
    """Показать историю миграций"""
    alembic_cfg = get_alembic_config()
    try:
        command.history(alembic_cfg)
    except Exception as e:
        logger.error(f"Ошибка: {e}")


def main():
    """Главная функция CLI"""
    import argparse

    parser = argparse.ArgumentParser(description='Утилита для работы с миграциями БД')
    subparsers = parser.add_subparsers(dest='command', help='Команды')

    # Команда upgrade
    upgrade_parser = subparsers.add_parser('upgrade', help='Применить миграции')
    upgrade_parser.add_argument('revision', nargs='?', default='head',
                                help='Версия для применения (по умолчанию: head)')

    # Команда downgrade
    downgrade_parser = subparsers.add_parser('downgrade', help='Откатить миграции')
    downgrade_parser.add_argument('revision', nargs='?', default='-1',
                                  help='Версия для отката (по умолчанию: -1)')

    # Команда create
    create_parser = subparsers.add_parser('create', help='Создать миграцию')
    create_parser.add_argument('message', help='Описание миграции')
    create_parser.add_argument('--no-autogenerate', action='store_true',
                               help='Не использовать автогенерацию')

    # Команда current
    subparsers.add_parser('current', help='Показать текущую версию')

    # Команда history
    subparsers.add_parser('history', help='Показать историю миграций')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'upgrade':
            upgrade(args.revision)
        elif args.command == 'downgrade':
            downgrade(args.revision)
        elif args.command == 'create':
            create_migration(args.message, autogenerate=not args.no_autogenerate)
        elif args.command == 'current':
            show_current()
        elif args.command == 'history':
            show_history()
    except Exception as e:
        logger.error(f"Ошибка выполнения команды: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

