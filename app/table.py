import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_logger import logger


def create_server_classification_table(df):
    """
    Создание таблицы классификации серверов
    """
    try:
        logger.info('Начало создания таблицы классификации серверов')
        logger.info(f'Размер входных данных: {df.shape[0]} строк, {df.shape[1]} столбцов')
        logger.info(f'Уникальных серверов: {df["vm"].nunique()}')
        logger.info(f'Уникальных метрик: {df["metric"].unique().tolist()}')

        # CPU данные
        cpu_data = df[df['metric'] == 'cpu.usage.average'].groupby('vm')['avg_value'].mean().reset_index()
        logger.info(f'CPU данные собраны: {len(cpu_data)} серверов')
        logger.debug(f'Пример CPU данных: {cpu_data.head().to_dict()}')

        # Memory данные
        mem_data = df[df['metric'] == 'mem.usage.average'].groupby('vm')['avg_value'].mean().reset_index()
        logger.info(f'Memory данные собраны: {len(mem_data)} серверов')
        logger.debug(f'Пример Memory данных: {mem_data.head().to_dict()}')

        # Объединяем данные
        classification = pd.merge(cpu_data, mem_data, on='vm', suffixes=('_cpu', '_mem'))
        logger.info(f'Данные объединены: {len(classification)} серверов после слияния')
        logger.debug(f'Структура объединенных данных:\n{classification.head()}')

        # Классифицируем
        logger.info('Правила классификации CPU:')
        logger.info('- "🟢 Низкая" если < 20%')
        logger.info('- "🟡 Нормальная" если 20-70%')
        logger.info('- "🔴 Высокая" если >= 70%')

        def classify_cpu(x):
            if x < 20:
                logger.debug(f'CPU значение {x}% классифицировано как "🟢 Низкая"')
                return '🟢 Низкая'
            elif x < 70:
                logger.debug(f'CPU значение {x}% классифицировано как "🟡 Нормальная"')
                return '🟡 Нормальная'
            else:
                logger.warning(f'CPU значение {x}% классифицировано как "🔴 Высокая" - требуется внимание!')
                return '🔴 Высокая'

        logger.info('Правила классификации Memory:')
        logger.info('- "🟢 Низкая" если < 30%')
        logger.info('- "🟡 Нормальная" если 30-80%')
        logger.info('- "🔴 Высокая" если >= 80%')

        def classify_mem(x):
            if x < 30:
                logger.debug(f'Memory значение {x}% классифицировано как "🟢 Низкая"')
                return '🟢 Низкая'
            elif x < 80:
                logger.debug(f'Memory значение {x}% классифицировано как "🟡 Нормальная"')
                return '🟡 Нормальная'
            else:
                logger.warning(f'Memory значение {x}% классифицировано как "🔴 Высокая" - требуется внимание!')
                return '🔴 Высокая'

        logger.info('Правила рекомендаций:')
        logger.info('- "Требуется масштабирование" если CPU или Memory в красной зоне')
        logger.info('- "Возможна консолидация" если CPU и Memory в зеленой зоне')
        logger.info('- "Нормальная работа" в остальных случаях')

        def get_recommendation(cpu_cat, mem_cat):
            if '🔴' in cpu_cat or '🔴' in mem_cat:
                logger.info(f'Рекомендация: "Требуется масштабирование" для CPU={cpu_cat}, Memory={mem_cat}')
                return 'Требуется масштабирование'
            elif '🟢' in cpu_cat and '🟢' in mem_cat:
                logger.info(f'Рекомендация: "Возможна консолидация" для CPU={cpu_cat}, Memory={mem_cat}')
                return 'Возможна консолидация'
            else:
                logger.info(f'Рекомендация: "Нормальная работа" для CPU={cpu_cat}, Memory={mem_cat}')
                return 'Нормальная работа'

        # Применяем классификацию
        classification['CPU Категория'] = classification['avg_value_cpu'].apply(classify_cpu)
        classification['Memory Категория'] = classification['avg_value_mem'].apply(classify_mem)
        classification['Рекомендация'] = classification.apply(
            lambda x: get_recommendation(x['CPU Категория'], x['Memory Категория']), axis=1
        )
        classification['Средний CPU %'] = classification['avg_value_cpu'].round(2)
        classification['Средняя Memory %'] = classification['avg_value_mem'].round(2)

        # Анализируем результаты
        cpu_categories = classification['CPU Категория'].value_counts()
        mem_categories = classification['Memory Категория'].value_counts()
        recommendations = classification['Рекомендация'].value_counts()

        logger.info('Статистика классификации CPU:')
        for category, count in cpu_categories.items():
            logger.info(f'  {category}: {count} серверов')

        logger.info('Статистика классификации Memory:')
        for category, count in mem_categories.items():
            logger.info(f'  {category}: {count} серверов')

        logger.info('Статистика рекомендаций:')
        for recommendation, count in recommendations.items():
            logger.info(f'  {recommendation}: {count} серверов')

        # Удаляем лишние столбцы
        result = classification[[
            'vm', 'Средний CPU %', 'CPU Категория',
            'Средняя Memory %', 'Memory Категория', 'Рекомендация'
        ]]

        # Переименовываем
        result = result.rename(columns={'vm': 'Сервер'})

        logger.info(f'Таблица классификации создана успешно: {len(result)} серверов')
        logger.debug(f'Пример результата:\n{result.head().to_string()}')

        # Логируем сервера требующие внимания
        critical_servers = result[
            (result['CPU Категория'].str.contains('🔴')) |
            (result['Memory Категория'].str.contains('🔴'))
            ]
        if len(critical_servers) > 0:
            logger.warning(f'Найдено серверов требующих внимания: {len(critical_servers)}')
            for _, server in critical_servers.iterrows():
                logger.warning(
                    f'Сервер {server["Сервер"]}: CPU={server["Средний CPU %"]}% '
                    f'({server["CPU Категория"]}), Memory={server["Средняя Memory %"]}% '
                    f'({server["Memory Категория"]})'
                )

        return result

    except Exception as e:
        logger.error(f'Ошибка при создании таблицы классификации: {str(e)}', exc_info=True)
        raise


def create_load_timeline(df, selected_server):
    """
    Создание таймлайна нагрузки для выбранного сервера
    """
    try:
        logger.info(f'Начало создания таймлайна нагрузки для сервера: {selected_server}')
        logger.info(f'Размер входных данных: {df.shape[0]} строк')

        # Проверяем наличие сервера в данных
        servers_in_data = df['vm'].unique()
        if selected_server not in servers_in_data:
            logger.error(
                f'Сервер "{selected_server}" не найден в данных. Доступные серверы: {servers_in_data.tolist()}')
            raise ValueError(f'Сервер "{selected_server}" не найден в данных')

        server_data = df[df['vm'] == selected_server]
        logger.info(f'Данные для сервера {selected_server}: {len(server_data)} записей')
        logger.info(f'Период данных: {server_data["date"].min()} - {server_data["date"].max()}')

        # CPU данные
        cpu_data = server_data[server_data['metric'] == 'cpu.usage.average']
        logger.info(f'CPU данных для {selected_server}: {len(cpu_data)} записей')
        if len(cpu_data) > 0:
            logger.debug(f'Статистика CPU: min={cpu_data["avg_value"].min():.2f}%, '
                         f'max={cpu_data["avg_value"].max():.2f}%, '
                         f'mean={cpu_data["avg_value"].mean():.2f}%')

        # Memory данные
        mem_data = server_data[server_data['metric'] == 'mem.usage.average']
        logger.info(f'Memory данных для {selected_server}: {len(mem_data)} записей')
        if len(mem_data) > 0:
            logger.debug(f'Статистика Memory: min={mem_data["avg_value"].min():.2f}%, '
                         f'max={mem_data["avg_value"].max():.2f}%, '
                         f'mean={mem_data["avg_value"].mean():.2f}%')

        # Disk данные
        disk_data = server_data[server_data['metric'] == 'disk.usage.average']
        logger.info(f'Disk данных для {selected_server}: {len(disk_data)} записей')
        if len(disk_data) > 0:
            logger.debug(f'Статистика Disk: min={disk_data["avg_value"].min():.2f} KB/s, '
                         f'max={disk_data["avg_value"].max():.2f} KB/s, '
                         f'mean={disk_data["avg_value"].mean():.2f} KB/s')

        # Проверяем наличие данных
        if len(cpu_data) == 0 and len(mem_data) == 0 and len(disk_data) == 0:
            logger.warning(
                f'Нет данных для сервера {selected_server}. Доступные метрики: {server_data["metric"].unique()}')
            return None

        # Создаем график
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('CPU Нагрузка', 'Использование памяти', 'Использование диска'),
            vertical_spacing=0.1,
            shared_xaxes=True
        )

        # CPU график
        if len(cpu_data) > 0:
            fig.add_trace(
                go.Scatter(x=cpu_data['date'], y=cpu_data['avg_value'],
                           name='CPU %', mode='lines+markers',
                           line=dict(color='blue', width=2)),
                row=1, col=1
            )
            logger.info('CPU график добавлен')
        else:
            logger.warning(f'Нет CPU данных для сервера {selected_server}')

        # Memory график
        if len(mem_data) > 0:
            fig.add_trace(
                go.Scatter(x=mem_data['date'], y=mem_data['avg_value'],
                           name='Memory %', mode='lines+markers',
                           line=dict(color='green', width=2)),
                row=2, col=1
            )
            logger.info('Memory график добавлен')
        else:
            logger.warning(f'Нет Memory данных для сервера {selected_server}')

        # Disk график
        if not disk_data.empty:
            fig.add_trace(
                go.Scatter(x=disk_data['date'], y=disk_data['avg_value'],
                           name='Disk KB/s', mode='lines+markers',
                           line=dict(color='orange', width=2)),
                row=3, col=1
            )
            logger.info('Disk график добавлен')
        else:
            logger.info(f'Нет Disk данных для сервера {selected_server}')

        # Пороговые линии
        if len(cpu_data) > 0:
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1,
                          annotation_text="Высокая нагрузка", annotation_position="top right")
            logger.debug('Пороговая линия для CPU добавлена (70%)')

        if len(mem_data) > 0:
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1,
                          annotation_text="Критично", annotation_position="top right")
            logger.debug('Пороговая линия для Memory добавлена (80%)')

        fig.update_layout(
            height=800,
            showlegend=True,
            title_text=f"Динамика нагрузки сервера: {selected_server}"
        )

        fig.update_xaxes(title_text="Дата", row=3, col=1)
        fig.update_yaxes(title_text="CPU %", row=1, col=1)
        fig.update_yaxes(title_text="Memory %", row=2, col=1)
        if not disk_data.empty:
            fig.update_yaxes(title_text="Disk KB/s", row=3, col=1)

        logger.info(f'Таймлайн нагрузки успешно создан для сервера: {selected_server}')

        # Логируем пиковые значения
        if len(cpu_data) > 0:
            max_cpu = cpu_data['avg_value'].max()
            if max_cpu >= 70:
                logger.warning(f'Максимальная CPU нагрузка для {selected_server}: {max_cpu:.2f}% (превышает порог 70%)')

        if len(mem_data) > 0:
            max_mem = mem_data['avg_value'].max()
            if max_mem >= 80:
                logger.warning(
                    f'Максимальная Memory нагрузка для {selected_server}: {max_mem:.2f}% (превышает порог 80%)')

        return fig

    except Exception as e:
        logger.error(f'Ошибка при создании таймлайна нагрузки для сервера {selected_server}: {str(e)}', exc_info=True)
        raise