import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_server_classification_table(df):
    """
    Создание таблицы классификации серверов
    """
    cpu_data = df[df['metric'] == 'cpu.usage.average'].groupby('vm')['avg_value'].mean().reset_index()
    mem_data = df[df['metric'] == 'mem.usage.average'].groupby('vm')['avg_value'].mean().reset_index()

    # Объединяем данные
    classification = pd.merge(cpu_data, mem_data, on='vm', suffixes=('_cpu', '_mem'))

    # Классифицируем
    def classify_cpu(x):
        if x < 20:
            return '🟢 Низкая'
        elif x < 70:
            return '🟡 Нормальная'
        else:
            return '🔴 Высокая'

    def classify_mem(x):
        if x < 30:
            return '🟢 Низкая'
        elif x < 80:
            return '🟡 Нормальная'
        else:
            return '🔴 Высокая'

    def get_recommendation(cpu_cat, mem_cat):
        if '🔴' in cpu_cat or '🔴' in mem_cat:
            return 'Требуется масштабирование'
        elif '🟢' in cpu_cat and '🟢' in mem_cat:
            return 'Возможна консолидация'
        else:
            return 'Нормальная работа'

    classification['CPU Категория'] = classification['avg_value_cpu'].apply(classify_cpu)
    classification['Memory Категория'] = classification['avg_value_mem'].apply(classify_mem)
    classification['Рекомендация'] = classification.apply(
        lambda x: get_recommendation(x['CPU Категория'], x['Memory Категория']), axis=1
    )
    classification['Средний CPU %'] = classification['avg_value_cpu'].round(2)
    classification['Средняя Memory %'] = classification['avg_value_mem'].round(2)

    # Удаляем лишние столбцы
    result = classification[[
        'vm', 'Средний CPU %', 'CPU Категория',
        'Средняя Memory %', 'Memory Категория', 'Рекомендация'
    ]]

    # Переименовываем
    result = result.rename(columns={'vm': 'Сервер'})

    return result


def create_load_timeline(df, selected_server):
    """
    Создание таймлайна нагрузки для выбранного сервера
    """
    server_data = df[df['vm'] == selected_server]

    # CPU данные
    cpu_data = server_data[server_data['metric'] == 'cpu.usage.average']

    # Memory данные
    mem_data = server_data[server_data['metric'] == 'mem.usage.average']

    # Disk данные (если есть)
    disk_data = server_data[server_data['metric'] == 'disk.usage.average']

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('CPU Нагрузка', 'Использование памяти', 'Использование диска'),
        vertical_spacing=0.1,
        shared_xaxes=True
    )

    # CPU график
    fig.add_trace(
        go.Scatter(x=cpu_data['date'], y=cpu_data['avg_value'],
                   name='CPU %', mode='lines+markers',
                   line=dict(color='blue', width=2)),
        row=1, col=1
    )

    # Memory график
    fig.add_trace(
        go.Scatter(x=mem_data['date'], y=mem_data['avg_value'],
                   name='Memory %', mode='lines+markers',
                   line=dict(color='green', width=2)),
        row=2, col=1
    )

    # Disk график (если есть данные)
    if not disk_data.empty:
        fig.add_trace(
            go.Scatter(x=disk_data['date'], y=disk_data['avg_value'],
                       name='Disk KB/s', mode='lines+markers',
                       line=dict(color='orange', width=2)),
            row=3, col=1
        )

    # Пороговые линии
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=1, col=1,
                  annotation_text="Высокая нагрузка", annotation_position="top right")
    fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1,
                  annotation_text="Критично", annotation_position="top right")

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

    return fig
