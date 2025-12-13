import plotly.express as px

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_logger import logger


def create_memory_heatmap(df):
    """
    Тепловая карта использования памяти по дням
    """
    try:
        logger.info("Начинаем создание тепловой карты использования памяти")

        # Проверка входных данных
        if df.empty:
            logger.warning("Получен пустой DataFrame для тепловой карты памяти")
            raise ValueError("DataFrame пустой")

        # Проверка наличия необходимых колонок
        required_columns = ['metric', 'vm', 'date', 'avg_value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            raise ValueError(f"Отсутствуют колонки: {missing_columns}")

        logger.debug(f"Размер входного DataFrame: {df.shape}")
        logger.debug(f"Колонки в DataFrame: {list(df.columns)}")

        usage_data = df[df['metric'] == 'mem.usage.average']

        if usage_data.empty:
            logger.warning("Нет данных с метрикой 'mem.usage.average'")
            # Создаем заглушку для пустых данных
            fig = create_empty_plot("Нет данных об использовании памяти")
            return fig

        logger.info(f"Найдено {len(usage_data)} записей об использовании памяти")

        # Подготовка данных для тепловой карты
        logger.debug("Подготовка pivot таблицы для тепловой карты")
        pivot_data = usage_data.pivot_table(
            values='avg_value',
            index='vm',
            columns='date',
            aggfunc='mean'
        )

        logger.debug(f"Размер pivot таблицы: {pivot_data.shape}")

        # Сортируем по максимальному использованию
        logger.debug("Сортировка данных по максимальному использованию")
        pivot_data['max_usage'] = pivot_data.max(axis=1)
        pivot_data = pivot_data.sort_values('max_usage', ascending=False)
        pivot_data = pivot_data.drop('max_usage', axis=1)

        # Создание тепловой карты
        logger.info("Создание тепловой карты Plotly")
        fig = px.imshow(
            pivot_data,
            labels=dict(x="Дата", y="Сервер", color="Использование памяти (%)"),
            title="Тепловая карта использования памяти",
            color_continuous_scale=[
                [0, "#2E8B57"],  # Low - green
                [0.3, "#90EE90"],  # Medium low - light green
                [0.7, "#FFD700"],  # Medium - yellow
                [0.8, "#FF8C00"],  # High - orange
                [1.0, "#FF4500"]  # Critical - red
            ],
            aspect="auto",
            text_auto='.0f'
        )

        # Настройка layout
        logger.debug("Настройка layout тепловой карты")
        fig.update_layout(
            height=700,
            xaxis_title="Дата",
            yaxis_title="Сервер",
            coloraxis_colorbar=dict(
                title="%",
                thickness=20,
                len=0.8
            ),
            title_font_size=16
        )

        logger.info("Тепловая карта использования памяти успешно создана")
        return fig

    except Exception as e:
        logger.error(f"Ошибка при создании тепловой карты памяти: {str(e)}", exc_info=True)
        # Возвращаем заглушку с ошибкой
        return create_error_plot(f"Ошибка: {str(e)}")


def create_memory_load_chart(df):
    """
    Создание графика использования памяти
    """
    try:
        logger.info("Начинаем создание графика использования памяти")

        # Проверка входных данных
        if df.empty:
            logger.warning("Получен пустой DataFrame для графика памяти")
            raise ValueError("DataFrame пустой")

        # Проверка наличия необходимых колонок
        required_columns = ['metric', 'vm', 'avg_value']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Отсутствуют необходимые колонки: {missing_columns}")
            raise ValueError(f"Отсутствуют колонки: {missing_columns}")

        logger.debug(f"Размер входного DataFrame: {df.shape}")

        # Фильтрация данных
        mem_data = df[df['metric'] == 'mem.usage.average']

        if mem_data.empty:
            logger.warning("Нет данных с метрикой 'mem.usage.average' для графика")
            return create_empty_plot("Нет данных об использовании памяти")

        logger.info(f"Найдено {len(mem_data)} записей для графика использования памяти")
        logger.debug(f"Уникальных серверов: {mem_data['vm'].nunique()}")

        # Группируем по серверам
        logger.debug("Группировка данных по серверам")
        avg_memory = mem_data.groupby('vm')['avg_value'].mean().sort_values(ascending=False).reset_index()

        logger.debug(f"Среднее использование памяти по серверам: {avg_memory['avg_value'].describe().to_dict()}")

        # Создание графика
        logger.info("Создание bar chart использования памяти")
        fig = px.bar(
            avg_memory,
            x='vm',
            y='avg_value',
            title="Среднее использование памяти по серверам",
            labels={'vm': 'Сервер', 'avg_value': 'Использование памяти (%)'},
            color='avg_value',
            color_continuous_scale='Blues'
        )

        # Настройка layout
        logger.debug("Настройка layout графика памяти")
        fig.update_layout(
            xaxis_tickangle=-45,
            height=500,
            xaxis_title="Сервер",
            yaxis_title="Использование памяти (%)",
            coloraxis_colorbar=dict(title="%"),
            title_font_size=16
        )

        # Добавляем горизонтальные линии порогов
        logger.debug("Добавление пороговых линий на график")
        fig.add_hline(
            y=80,
            line_dash="dash",
            line_color="red",
            annotation_text="Критический порог 80%",
            annotation_position="top right"
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color="green",
            annotation_text="Порог низкой нагрузки 30%",
            annotation_position="bottom right"
        )

        # Добавляем аннотации для высоких значений
        high_usage = avg_memory[avg_memory['avg_value'] > 80]
        if not high_usage.empty:
            logger.warning(f"Найдено {len(high_usage)} серверов с использованием памяти > 80%")
            for _, row in high_usage.iterrows():
                fig.add_annotation(
                    x=row['vm'],
                    y=row['avg_value'],
                    text=f"{row['avg_value']:.1f}%",
                    showarrow=True,
                    arrowhead=1,
                    ax=0,
                    ay=-40,
                    bgcolor="red",
                    font=dict(color="white")
                )

        logger.info("График использования памяти успешно создан")
        return fig

    except Exception as e:
        logger.error(f"Ошибка при создании графика использования памяти: {str(e)}", exc_info=True)
        return create_error_plot(f"Ошибка: {str(e)}")


def create_empty_plot(message):
    """
    Создает пустой график с сообщением
    """
    logger.debug(f"Создание пустого графика с сообщением: {message}")

    fig = px.bar(title=message)
    fig.update_layout(
        height=400,
        annotations=[
            dict(
                text=message,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=16)
            )
        ]
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
        ]
    )
    return fig


def log_memory_statistics(df):
    """
    Логирование статистики по использованию памяти
    """
    try:
        if df.empty or 'metric' not in df.columns:
            return

        mem_data = df[df['metric'] == 'mem.usage.average']

        if mem_data.empty:
            logger.info("Нет данных об использовании памяти для статистики")
            return

        # Основная статистика
        stats = mem_data['avg_value'].describe()

        logger.info(f"Статистика использования памяти:")
        logger.info(f"  Количество записей: {int(stats['count'])}")
        logger.info(f"  Среднее значение: {stats['mean']:.2f}%")
        logger.info(f"  Минимальное значение: {stats['min']:.2f}%")
        logger.info(f"  Максимальное значение: {stats['max']:.2f}%")
        logger.info(f"  25-й перцентиль: {stats['25%']:.2f}%")
        logger.info(f"  50-й перцентиль (медиана): {stats['50%']:.2f}%")
        logger.info(f"  75-й перцентиль: {stats['75%']:.2f}%")

        # Дополнительная статистика
        high_usage = mem_data[mem_data['avg_value'] > 80]
        normal_usage = mem_data[(mem_data['avg_value'] >= 30) & (mem_data['avg_value'] <= 80)]
        low_usage = mem_data[mem_data['avg_value'] < 30]

        logger.info(f"  Высокая нагрузка (>80%): {len(high_usage)} записей")
        logger.info(f"  Нормальная нагрузка (30-80%): {len(normal_usage)} записей")
        logger.info(f"  Низкая нагрузка (<30%): {len(low_usage)} записей")

        # Статистика по серверам
        server_stats = mem_data.groupby('vm')['avg_value'].agg(['mean', 'max', 'min'])
        critical_servers = server_stats[server_stats['max'] > 80]

        if not critical_servers.empty:
            logger.warning(f"Серверы с критическим использованием памяти (>80%):")
            for server, row in critical_servers.iterrows():
                logger.warning(f"  {server}: макс. {row['max']:.1f}%, средн. {row['mean']:.1f}%")

    except Exception as e:
        logger.error(f"Ошибка при логировании статистики памяти: {str(e)}", exc_info=True)
