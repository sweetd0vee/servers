import plotly.express as px

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_logger import logger


def create_cpu_heatmap(df):
    """
    Тепловая карта использования CPU по дням
    """
    try:
        logger.info("Начинаем создание тепловой карты использования CPU")

        # Проверка входных данных
        if df.empty:
            logger.warning("Получен пустой DataFrame для тепловой карты CPU")
            raise ValueError("DataFrame пустой")

        # Проверка наличия необходимых колонок
        required_columns = ['metric', 'vm', 'date', 'avg_value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            raise ValueError(f"Отсутствуют колонки: {missing_columns}")

        logger.debug(f"Размер входного DataFrame: {df.shape}")
        logger.debug(f"Колонки в DataFrame: {list(df.columns)}")

        # Фильтрация данных по CPU
        usage_data = df[df['metric'] == 'cpu.usage.average']

        if usage_data.empty:
            logger.warning("Нет данных с метрикой 'cpu.usage.average'")
            # Создаем заглушку для пустых данных
            fig = create_empty_plot("Нет данных об использовании CPU")
            return fig

        logger.info(f"Найдено {len(usage_data)} записей об использовании CPU")
        logger.debug(f"Уникальных серверов: {usage_data['vm'].nunique()}")
        logger.debug(f"Диапазон дат: от {usage_data['date'].min()} до {usage_data['date'].max()}")

        # Подготовка данных для тепловой карты
        logger.debug("Подготовка pivot таблицы для тепловой карты CPU")
        pivot_data = usage_data.pivot_table(
            values='avg_value',
            index='vm',
            columns='date',
            aggfunc='mean'
        )

        logger.debug(f"Размер pivot таблицы: {pivot_data.shape}")

        if pivot_data.empty:
            logger.warning("Pivot таблица пустая после обработки")
            fig = create_empty_plot("Недостаточно данных для тепловой карты CPU")
            return fig

        # Сортируем по максимальному использованию
        logger.debug("Сортировка данных по максимальному использованию CPU")
        pivot_data['max_usage'] = pivot_data.max(axis=1)

        # Логируем статистику перед сортировкой
        logger.debug(f"Максимальное использование CPU по серверам: {pivot_data['max_usage'].describe().to_dict()}")

        pivot_data = pivot_data.sort_values('max_usage', ascending=False)
        pivot_data = pivot_data.drop('max_usage', axis=1)

        # Проверяем, есть ли критически загруженные серверы
        critical_servers = pivot_data.apply(lambda row: row.max() > 80, axis=1).sum()
        if critical_servers > 0:
            logger.warning(f"Найдено {critical_servers} серверов с критической нагрузкой CPU (>80%)")

        # Создание тепловой карты
        logger.info("Создание тепловой карты CPU с помощью Plotly")
        fig = px.imshow(
            pivot_data,
            labels=dict(x="Дата", y="Сервер", color="Использование CPU (%)"),
            title="Тепловая карта использования CPU",
            color_continuous_scale=[
                [0, "#2E8B57"],  # Low - green
                [0.3, "#90EE90"],  # Medium low - light green
                [0.7, "#FFD700"],  # Medium - yellow
                [0.8, "#FF8C00"],  # High - orange
                [1.0, "#FF4500"]  # Critical - red
            ],
            aspect="auto",
            text_auto='.0f',
            range_color=[0, 100]  # Ограничиваем диапазон 0-100%
        )

        # Настройка layout
        logger.debug("Настройка layout тепловой карты CPU")
        fig.update_layout(
            height=700,
            xaxis_title="Дата",
            yaxis_title="Сервер",
            coloraxis_colorbar=dict(
                title="%",
                thickness=20,
                len=0.8
            ),
            title_font_size=16,
            margin=dict(l=50, r=50, t=80, b=50)
        )

        # Настройка осей для лучшей читаемости
        fig.update_xaxes(tickangle=45)

        logger.info(f"Тепловая карта CPU успешно создана. Серверов: {pivot_data.shape[0]}, дней: {pivot_data.shape[1]}")
        return fig

    except Exception as e:
        logger.error(f"Ошибка при создании тепловой карты CPU: {str(e)}", exc_info=True)
        # Возвращаем заглушку с ошибкой
        return create_error_plot(f"Ошибка создания тепловой карты CPU: {str(e)}")


def create_cpu_load_chart(df):
    """
    Создание графика использования CPU
    """
    try:
        logger.info("Начинаем создание графика использования CPU")

        # Проверка входных данных
        if df.empty:
            logger.warning("Получен пустой DataFrame для графика CPU")
            raise ValueError("DataFrame пустой")

        # Проверка наличия необходимых колонок
        required_columns = ['metric', 'vm', 'avg_value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            raise ValueError(f"Отсутствуют колонки: {missing_columns}")

        logger.debug(f"Размер входного DataFrame: {df.shape}")

        # Фильтрация данных
        cpu_data = df[df['metric'] == 'cpu.usage.average']

        if cpu_data.empty:
            logger.warning("Нет данных с метрикой 'cpu.usage.average' для графика")
            return create_empty_plot("Нет данных об использовании CPU")

        logger.info(f"Найдено {len(cpu_data)} записей для графика использования CPU")
        logger.debug(f"Уникальных серверов: {cpu_data['vm'].nunique()}")

        # Группируем по серверам
        logger.debug("Группировка данных по серверам для CPU")
        avg_cpu = cpu_data.groupby('vm')['avg_value'].mean().sort_values(ascending=False).reset_index()

        # Логируем статистику
        cpu_stats = avg_cpu['avg_value'].describe()
        logger.debug(f"Статистика CPU по серверам: {cpu_stats.to_dict()}")

        # Проверяем критические значения
        critical_count = (avg_cpu['avg_value'] > 80).sum()
        high_count = ((avg_cpu['avg_value'] > 70) & (avg_cpu['avg_value'] <= 80)).sum()

        if critical_count > 0:
            logger.warning(f"Найдено {critical_count} серверов с критической нагрузкой CPU (>80%)")
        if high_count > 0:
            logger.info(f"Найдено {high_count} серверов с высокой нагрузкой CPU (70-80%)")

        # Создание графика
        logger.info("Создание bar chart использования CPU")
        fig = px.bar(
            avg_cpu,
            x='vm',
            y='avg_value',
            title="Среднее использование CPU по серверам",
            labels={'vm': 'Сервер', 'avg_value': 'Использование CPU (%)'},
            color='avg_value',
            color_continuous_scale='Blues',
            range_color=[0, 100]  # Ограничиваем цветовую шкалу
        )

        # Настройка layout
        logger.debug("Настройка layout графика CPU")
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500,
            xaxis_title="Сервер",
            yaxis_title="Использование CPU (%)",
            coloraxis_colorbar=dict(
                title="%",
                thickness=15,
                len=0.7
            ),
            title_font_size=16,
            showlegend=False,
            margin=dict(l=50, r=50, t=80, b=100)
        )

        # Добавляем горизонтальные линии порогов
        logger.debug("Добавление пороговых линий на график CPU")
        fig.add_hline(
            y=80,
            line_dash="dash",
            line_color="red",
            annotation_text="Критический порог 80%",
            annotation_position="top right",
            annotation_font_size=12
        )
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color="orange",
            annotation_text="Высокая нагрузка 70%",
            annotation_position="top right",
            annotation_font_size=12
        )
        fig.add_hline(
            y=20,
            line_dash="dash",
            line_color="green",
            annotation_text="Низкая нагрузка 20%",
            annotation_position="bottom right",
            annotation_font_size=12
        )

        # Добавляем аннотации для критических значений
        critical_servers = avg_cpu[avg_cpu['avg_value'] > 80]
        if not critical_servers.empty:
            logger.warning(f"Добавляем аннотации для {len(critical_servers)} серверов с CPU > 80%")
            for _, row in critical_servers.iterrows():
                fig.add_annotation(
                    x=row['vm'],
                    y=row['avg_value'],
                    text=f"⚠️ {row['avg_value']:.1f}%",
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40,
                    bgcolor="red",
                    font=dict(color="white", size=10)
                )

        # Добавляем значения на столбцы
        fig.update_traces(
            texttemplate='%{y:.1f}%',
            textposition='outside'
        )

        logger.info(f"График использования CPU успешно создан. Обработано серверов: {len(avg_cpu)}")
        return fig

    except Exception as e:
        logger.error(f"Ошибка при создании графика использования CPU: {str(e)}", exc_info=True)
        return create_error_plot(f"Ошибка создания графика CPU: {str(e)}")


def create_empty_plot(message):
    """
    Создает пустой график с сообщением
    """
    logger.debug(f"Создание пустого графика с сообщением: {message}")

    fig = px.bar(title=message)
    fig.update_layout(
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16, color="gray")
            )
        ],
        plot_bgcolor='white'
    )
    return fig


def create_error_plot(error_message):
    """
    Создает график с сообщением об ошибке
    """
    logger.error(f"Создание графика с ошибкой: {error_message}")

    fig = px.bar(title="Ошибка при создании графика")
    fig.update_layout(
        height=400,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=f"Ошибка: {error_message}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14, color="red")
            )
        ],
        plot_bgcolor='white'
    )
    return fig


def log_cpu_statistics(df):
    """
    Логирование статистики по использованию CPU
    """
    try:
        if df.empty or 'metric' not in df.columns:
            logger.warning("Нет данных для статистики CPU")
            return

        cpu_data = df[df['metric'] == 'cpu.usage.average']

        if cpu_data.empty:
            logger.info("Нет данных об использовании CPU для статистики")
            return

        # Основная статистика
        stats = cpu_data['avg_value'].describe()

        logger.info("=" * 50)
        logger.info("СТАТИСТИКА ИСПОЛЬЗОВАНИЯ CPU:")
        logger.info(f"  Всего записей: {int(stats['count']):,}")
        logger.info(f"  Среднее значение: {stats['mean']:.2f}%")
        logger.info(f"  Минимальное значение: {stats['min']:.2f}%")
        logger.info(f"  Максимальное значение: {stats['max']:.2f}%")
        logger.info(f"  Стандартное отклонение: {stats['std']:.2f}%")
        logger.info(f"  Медиана (50-й перцентиль): {stats['50%']:.2f}%")

        # Статистика по категориям нагрузки
        critical_cpu = cpu_data[cpu_data['avg_value'] > 80]
        high_cpu = cpu_data[(cpu_data['avg_value'] > 70) & (cpu_data['avg_value'] <= 80)]
        normal_cpu = cpu_data[(cpu_data['avg_value'] >= 20) & (cpu_data['avg_value'] <= 70)]
        low_cpu = cpu_data[cpu_data['avg_value'] < 20]

        logger.info("  Распределение по категориям:")
        logger.info(
            f"    🔴 Критическая (>80%): {len(critical_cpu):,} записей ({len(critical_cpu) / len(cpu_data) * 100:.1f}%)")
        logger.info(f"    🟠 Высокая (70-80%): {len(high_cpu):,} записей ({len(high_cpu) / len(cpu_data) * 100:.1f}%)")
        logger.info(
            f"    🟡 Нормальная (20-70%): {len(normal_cpu):,} записей ({len(normal_cpu) / len(cpu_data) * 100:.1f}%)")
        logger.info(f"    🟢 Низкая (<20%): {len(low_cpu):,} записей ({len(low_cpu) / len(cpu_data) * 100:.1f}%)")

        # Статистика по серверам
        server_stats = cpu_data.groupby('vm')['avg_value'].agg(['mean', 'max', 'min', 'std', 'count'])

        # Критические серверы
        critical_servers = server_stats[server_stats['max'] > 80]
        if not critical_servers.empty:
            logger.warning("  СЕРВЕРЫ С КРИТИЧЕСКОЙ НАГРУЗКОЙ CPU (>80%):")
            for server, row in critical_servers.iterrows():
                logger.warning(f"    ⚠️  {server}: макс. {row['max']:.1f}%, средн. {row['mean']:.1f}%")

        # Серверы с высокой нагрузкой
        high_servers = server_stats[(server_stats['max'] > 70) & (server_stats['max'] <= 80)]
        if not high_servers.empty:
            logger.info(f"  Серверов с высокой нагрузкой CPU: {len(high_servers)}")

        logger.info(f"  Всего уникальных серверов: {len(server_stats)}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Ошибка при логировании статистики CPU: {str(e)}", exc_info=True)


# Декоратор для автоматического логирования
def log_cpu_function(func):
    """Декоратор для логирования вызовов функций CPU"""

    def wrapper(*args, **kwargs):
        logger.debug(f"Вызов функции CPU: {func.__name__}")
        logger.debug(f"Аргументы: args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Функция {func.__name__} успешно выполнена")
            return result
        except Exception as e:
            logger.error(f"Ошибка в функции {func.__name__}: {str(e)}", exc_info=True)
            raise

    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper
