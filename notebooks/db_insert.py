import psycopg2
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime
import uuid
from tqdm import tqdm
from base_logger import logger


# Конфигурация базы данных
DB_CONFIG = {
    'host': 'localhost',  # или IP-адрес Docker контейнера
    'port': '5432',
    'database': 'server_metrics',  # имя вашей базы данных
    'user': 'postgres',
    'password': 'postgres'  # замените на ваш пароль
}


def read_excel_file(file_path):
    """Чтение данных из Excel файла"""
    try:
        # Читаем Excel файл
        df = pd.read_excel(file_path, sheet_name=0)  # sheet_name=0 для первого листа

        # Проверяем наличие необходимых колонок
        required_columns = ['vm', 'date', 'metric', 'max_value', 'min_value', 'avg_value']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Отсутствуют необходимые колонки: {missing_columns}")

        logger.info(f"Успешно прочитан файл: {file_path}")
        logger.info(f"Количество строк: {len(df)}")
        logger.info(f"Колонки: {df.columns.tolist()}")

        return df

    except Exception as e:
        logger.error(f"Ошибка чтения Excel файла: {e}")
        raise


def prepare_data(df):
    """Подготовка данных для вставки"""
    try:
        # Создаем копию данных
        data = df.copy()

        # Преобразуем дату в формат datetime
        data['date'] = pd.to_datetime(data['date'], errors='coerce')

        # Проверяем корректность преобразования дат
        invalid_dates = data['date'].isna().sum()
        if invalid_dates > 0:
            logger.warning(f"Найдено {invalid_dates} некорректных дат")

        # Преобразуем числовые колонки
        numeric_columns = ['max_value', 'min_value', 'avg_value']
        for col in numeric_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')

        # Генерируем UUID для каждой строки
        data['id'] = [str(uuid.uuid4()) for _ in range(len(data))]

        # Добавляем created_at
        data['created_at'] = datetime.now()

        # Выбираем только необходимые колонки в правильном порядке
        final_columns = ['id', 'vm', 'date', 'metric', 'max_value', 'min_value', 'avg_value', 'created_at']
        data = data[final_columns]

        # Удаляем строки с NaN значениями в ключевых полях
        original_count = len(data)
        data = data.dropna(subset=['vm', 'date', 'metric'])
        removed_count = original_count - len(data)

        if removed_count > 0:
            logger.warning(f"Удалено {removed_count} строк с отсутствующими ключевыми значениями")

        logger.info(f"Подготовлено {len(data)} строк для вставки")

        return data

    except Exception as e:
        logger.error(f"Ошибка подготовки данных: {e}")
        raise


def insert_data(df: pd.DataFrame):
    connection = psycopg2.connect(
        dbname=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        password=DB_CONFIG['password']
    )
    cur = connection.cursor()
    for i in tqdm(range(len(df))):
        row = list(df.iloc[i])
        # date and created_date
        row[2] = str(row[2])
        row[-1] = str(row[-1])
        row = tuple(row)
        query = f"INSERT INTO server_metrics (id, vm, date, metric, max_value, min_value, avg_value, created_at) \n" \
                f"VALUES {row}"
        try:
            cur.execute(query)
            connection.commit()
        except Exception as e:
            logger.info(f"Ошибка в ставке данных: {row}, {e}")

    cur.close()
    connection.close()
    return


def main():
    filepath = '../data/metrics.xlsx'
    df = read_excel_file(filepath)
    prepared_data = prepare_data(df)
    insert_data(prepared_data)


if __name__ == '__main__':
    main()