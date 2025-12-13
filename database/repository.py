"""
Репозиторий для работы с метриками серверов в базе данных
Использует SQLAlchemy для единообразной работы с БД
"""
import pandas as pd
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from database.connection import get_db, SessionLocal
from database.models import Servers
from base_logger import logger


class MetricsRepository:
    """Репозиторий для работы с метриками серверов"""

    def __init__(self, db: Optional[Session] = None):
        """
        Инициализация репозитория

        Args:
            db: SQLAlchemy сессия. Если не указана, будет создана новая
        """
        self.db = db

    def __enter__(self):
        """Контекстный менеджер для автоматического управления сессией"""
        if self.db is None:
            self.db = SessionLocal()
            self._own_session = True
        else:
            self._own_session = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие сессии при выходе из контекста"""
        if self._own_session and self.db:
            self.db.close()

    def get_all_metrics(
            self,
            vm: Optional[str] = None,
            start_date: Optional[date] = None,
            end_date: Optional[date] = None,
            metric: Optional[str] = None,
            limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Получение всех метрик с фильтрацией

        Args:
            vm: Фильтр по имени сервера
            start_date: Начальная дата
            end_date: Конечная дата
            metric: Фильтр по метрике (поддержка LIKE)
            limit: Ограничение количества записей

        Returns:
            DataFrame с метриками
        """
        try:
            query = self.db.query(Servers)

            # Применяем фильтры
            if vm:
                query = query.filter(Servers.vm == vm)

            if start_date:
                query = query.filter(Servers.date >= start_date)

            if end_date:
                query = query.filter(Servers.date <= end_date)

            if metric:
                query = query.filter(Servers.metric.like(f'%{metric}%'))

            # Сортировка
            query = query.order_by(Servers.vm, Servers.date, Servers.metric)

            # Ограничение
            if limit:
                query = query.limit(limit)

            # Выполняем запрос
            results = query.all()

            # Преобразуем в DataFrame
            data = []
            for row in results:
                data.append({
                    'vm': row.vm,
                    'date': row.date,
                    'metric': row.metric,
                    'max_value': float(row.max_value) if row.max_value else None,
                    'min_value': float(row.min_value) if row.min_value else None,
                    'avg_value': float(row.avg_value) if row.avg_value else None,
                    'created_at': row.created_at,
                })

            df = pd.DataFrame(data)

            if not df.empty:
                # Преобразуем дату в datetime если нужно
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])

            logger.info(f"Получено {len(df)} записей из базы данных")
            return df

        except Exception as e:
            logger.error(f"Ошибка при получении метрик: {e}", exc_info=True)
            return pd.DataFrame()

    def get_metrics_by_server(self, vm: str) -> pd.DataFrame:
        """
        Получение всех метрик для конкретного сервера

        Args:
            vm: Имя сервера

        Returns:
            DataFrame с метриками сервера
        """
        return self.get_all_metrics(vm=vm)

    def get_metrics_by_date_range(
            self,
            start_date: date,
            end_date: date,
            vm: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Получение метрик за период

        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            vm: Опциональный фильтр по серверу

        Returns:
            DataFrame с метриками
        """
        return self.get_all_metrics(
            vm=vm,
            start_date=start_date,
            end_date=end_date
        )

    def get_unique_servers(self) -> List[str]:
        """
        Получение списка уникальных серверов

        Returns:
            Список имен серверов
        """
        try:
            servers = self.db.query(Servers.vm).distinct().order_by(Servers.vm).all()
            return [s[0] for s in servers]
        except Exception as e:
            logger.error(f"Ошибка при получении списка серверов: {e}")
            return []

    def get_unique_metrics(self) -> List[str]:
        """
        Получение списка уникальных метрик

        Returns:
            Список метрик
        """
        try:
            metrics = self.db.query(Servers.metric).distinct().order_by(Servers.metric).all()
            return [m[0] for m in metrics]
        except Exception as e:
            logger.error(f"Ошибка при получении списка метрик: {e}")
            return []

    def get_date_range(self) -> Dict[str, Optional[date]]:
        """
        Получение диапазона дат в базе данных

        Returns:
            Словарь с 'min_date' и 'max_date'
        """
        try:
            min_date = self.db.query(func.min(Servers.date)).scalar()
            max_date = self.db.query(func.max(Servers.date)).scalar()

            return {
                'min_date': min_date,
                'max_date': max_date
            }
        except Exception as e:
            logger.error(f"Ошибка при получении диапазона дат: {e}")
            return {'min_date': None, 'max_date': None}

    def insert_metric(
            self,
            vm: str,
            date: date,
            metric: str,
            max_value: Optional[float] = None,
            min_value: Optional[float] = None,
            avg_value: Optional[float] = None
    ) -> bool:
        """
        Вставка одной метрики

        Args:
            vm: Имя сервера
            date: Дата
            metric: Название метрики
            max_value: Максимальное значение
            min_value: Минимальное значение
            avg_value: Среднее значение

        Returns:
            True если успешно, False в противном случае
        """
        try:
            # Проверяем существование записи
            existing = self.db.query(Servers).filter(
                and_(
                    Servers.vm == vm,
                    Servers.date == date,
                    Servers.metric == metric
                )
            ).first()

            if existing:
                # Обновляем существующую запись
                existing.max_value = max_value
                existing.min_value = min_value
                existing.avg_value = avg_value
            else:
                # Создаем новую запись
                new_metric = Servers(
                    vm=vm,
                    date=date,
                    metric=metric,
                    max_value=max_value,
                    min_value=min_value,
                    avg_value=avg_value
                )
                self.db.add(new_metric)

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Ошибка при вставке метрики: {e}", exc_info=True)
            self.db.rollback()
            return False

    def insert_from_dataframe(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        Массовая вставка данных из DataFrame

        Args:
            df: DataFrame с колонками: vm, date, metric, max_value, min_value, avg_value

        Returns:
            Словарь с количеством успешных и неудачных вставок
        """
        success_count = 0
        error_count = 0

        try:
            # Проверяем необходимые колонки
            required_columns = ['vm', 'date', 'metric', 'avg_value']
            missing = [col for col in required_columns if col not in df.columns]

            if missing:
                logger.error(f"Отсутствуют обязательные колонки: {missing}")
                return {'success': 0, 'errors': len(df)}

            # Преобразуем дату если нужно
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date

            # Вставляем данные построчно
            for _, row in df.iterrows():
                try:
                    result = self.insert_metric(
                        vm=str(row['vm']),
                        date=row['date'],
                        metric=str(row['metric']),
                        max_value=float(row['max_value']) if pd.notna(row.get('max_value')) else None,
                        min_value=float(row['min_value']) if pd.notna(row.get('min_value')) else None,
                        avg_value=float(row['avg_value']) if pd.notna(row['avg_value']) else None
                    )

                    if result:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    logger.warning(f"Ошибка при вставке строки {_}: {e}")
                    error_count += 1
                    continue

            logger.info(f"Вставлено {success_count} записей, ошибок: {error_count}")
            return {'success': success_count, 'errors': error_count}

        except Exception as e:
            logger.error(f"Ошибка при массовой вставке: {e}", exc_info=True)
            return {'success': success_count, 'errors': error_count + len(df) - success_count}

    def get_server_summary(self, vm: str) -> Dict[str, Any]:
        """
        Получение сводной информации по серверу

        Args:
            vm: Имя сервера

        Returns:
            Словарь со сводной информацией
        """
        try:
            metrics = self.get_metrics_by_server(vm)

            if metrics.empty:
                return {
                    'vm': vm,
                    'cpu_avg': 0,
                    'cpu_max': 0,
                    'mem_avg': 0,
                    'mem_max': 0,
                    'total_metrics': 0
                }

            # CPU метрики
            cpu_data = metrics[metrics['metric'].str.contains('cpu.usage', case=False, na=False)]
            cpu_avg = cpu_data['avg_value'].mean() if not cpu_data.empty else 0
            cpu_max = cpu_data['avg_value'].max() if not cpu_data.empty else 0

            # Memory метрики
            mem_data = metrics[metrics['metric'].str.contains('mem.usage', case=False, na=False)]
            mem_avg = mem_data['avg_value'].mean() if not mem_data.empty else 0
            mem_max = mem_data['avg_value'].max() if not mem_data.empty else 0

            return {
                'vm': vm,
                'cpu_avg': round(cpu_avg, 2),
                'cpu_max': round(cpu_max, 2),
                'mem_avg': round(mem_avg, 2),
                'mem_max': round(mem_max, 2),
                'total_metrics': len(metrics)
            }

        except Exception as e:
            logger.error(f"Ошибка при получении сводки по серверу {vm}: {e}")
            return {
                'vm': vm,
                'cpu_avg': 0,
                'cpu_max': 0,
                'mem_avg': 0,
                'mem_max': 0,
                'total_metrics': 0
            }

    def delete_old_metrics(self, days: int = 90) -> int:
        """
        Удаление старых метрик (старше указанного количества дней)

        Args:
            days: Количество дней для хранения

        Returns:
            Количество удаленных записей
        """
        try:
            cutoff_date = datetime.now().date() - pd.Timedelta(days=days)

            deleted = self.db.query(Servers).filter(
                Servers.date < cutoff_date
            ).delete()

            self.db.commit()
            logger.info(f"Удалено {deleted} записей старше {days} дней")
            return deleted

        except Exception as e:
            logger.error(f"Ошибка при удалении старых метрик: {e}")
            self.db.rollback()
            return 0


def get_metrics_from_db(
        vm: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        metric: Optional[str] = None
) -> pd.DataFrame:
    """
    Удобная функция для получения метрик из БД

    Args:
        vm: Фильтр по серверу
        start_date: Начальная дата
        end_date: Конечная дата
        metric: Фильтр по метрике

    Returns:
        DataFrame с метриками
    """
    with MetricsRepository() as repo:
        return repo.get_all_metrics(
            vm=vm,
            start_date=start_date,
            end_date=end_date,
            metric=metric
        )

