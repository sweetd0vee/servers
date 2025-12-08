import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import warnings
import json
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv

# Загружаем переменные окружения (для API ключей)
load_dotenv()

warnings.filterwarnings('ignore')


# Настройка страницы
st.set_page_config(
    page_title="Дашборд мониторинга серверов",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS для улучшения отображения
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        padding: 20px 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #1E3A8A;
        margin: 10px 0;
    }
    .warning-card {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .success-card {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_and_prepare_data():
    """Загрузка и подготовка данных"""
    # Чтение данных из файла
    df = pd.read_excel("data/metrics.xlsx")

    # Преобразование даты
    df['date'] = pd.to_datetime(df['date'])

    # Создание классификации нагрузки
    def classify_load(value, metric_type):
        if metric_type == 'cpu':
            if value < 20:
                return 'Низкая', 'success', '#28a745'
            elif value < 70:
                return 'Нормальная', 'warning', '#ffc107'
            else:
                return 'Высокая', 'danger', '#dc3545'
        elif metric_type == 'mem':
            if value < 30:
                return 'Низкая', 'success', '#28a745'
            elif value < 80:
                return 'Нормальная', 'warning', '#ffc107'
            else:
                return 'Высокая', 'danger', '#dc3545'
        else:
            return 'Нормальная', 'info', '#17a2b8'

    # Добавляем классификацию
    for idx, row in df.iterrows():
        if 'cpu.usage' in row['metric']:
            category, _, _ = classify_load(row['avg_value'], 'cpu')
            df.at[idx, 'load_category'] = category
            df.at[idx, 'metric_group'] = 'CPU'
        elif 'mem.usage' in row['metric']:
            category, _, _ = classify_load(row['avg_value'], 'mem')
            df.at[idx, 'load_category'] = category
            df.at[idx, 'metric_group'] = 'Память'
        elif 'disk.usage' in row['metric']:
            df.at[idx, 'load_category'] = 'Нормальная'
            df.at[idx, 'metric_group'] = 'Диск'
        elif 'net.usage' in row['metric']:
            df.at[idx, 'load_category'] = 'Нормальная'
            df.at[idx, 'metric_group'] = 'Сеть'
        else:
            df.at[idx, 'load_category'] = 'Нормальная'
            df.at[idx, 'metric_group'] = 'Другое'

    return df


def create_summary_metrics(df):
    """Создание карточек с метриками"""
    # Общие метрики
    total_servers = df['vm'].nunique()
    start_date = df['date'].min().strftime('%d.%m.%Y')
    end_date = df['date'].max().strftime('%d.%m.%Y')

    # Анализ CPU нагрузки
    cpu_data = df[df['metric'] == 'cpu.usage.average'].copy()
    cpu_data['cpu_category'] = cpu_data['avg_value'].apply(
        lambda x: 'Низкая' if x < 20 else ('Высокая' if x > 70 else 'Нормальная')
    )

    # Анализ Memory нагрузки
    mem_data = df[df['metric'] == 'mem.usage.average'].copy()
    mem_data['mem_category'] = mem_data['avg_value'].apply(
        lambda x: 'Низкая' if x < 30 else ('Высокая' if x > 80 else 'Нормальная')
    )

    # Подсчет по категориям
    cpu_low = cpu_data[cpu_data['cpu_category'] == 'Низкая']['vm'].nunique()
    cpu_normal = cpu_data[cpu_data['cpu_category'] == 'Нормальная']['vm'].nunique()
    cpu_high = cpu_data[cpu_data['cpu_category'] == 'Высокая']['vm'].nunique()

    return {
        'total_servers': total_servers,
        'period': f"{start_date} - {end_date}",
        'cpu_low': cpu_low,
        'cpu_normal': cpu_normal,
        'cpu_high': cpu_high,
        'mem_low': mem_data[mem_data['mem_category'] == 'Низкая']['vm'].nunique(),
        'mem_normal': mem_data[mem_data['mem_category'] == 'Нормальная']['vm'].nunique(),
        'mem_high': mem_data[mem_data['mem_category'] == 'Высокая']['vm'].nunique()
    }


def create_cpu_heatmap(df):
    """Тепловая карта использования cpu по дням"""
    usage_data = df[df['metric'] == 'cpu.usage.average']

    pivot_data = usage_data.pivot_table(
        values='avg_value',
        index='vm',
        columns='date',
        aggfunc='mean'
    )

    # Сортируем по максимальному использованию
    pivot_data['max_usage'] = pivot_data.max(axis=1)
    pivot_data = pivot_data.sort_values('max_usage', ascending=False)
    pivot_data = pivot_data.drop('max_usage', axis=1)

    fig = px.imshow(
        pivot_data,
        labels=dict(x="Дата", y="Сервер", color="Использование cpu (%)"),
        title="Тепловая карта использования cpu",
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

    fig.update_layout(
        height=700,
        xaxis_title="Дата",
        yaxis_title="Сервер",
        coloraxis_colorbar=dict(
            title="%",
            thickness=20,
            len=0.8
        )
    )

    return fig


def create_memory_heatmap(df):
    """Тепловая карта использования памяти по дням"""
    usage_data = df[df['metric'] == 'mem.usage.average']

    pivot_data = usage_data.pivot_table(
        values='avg_value',
        index='vm',
        columns='date',
        aggfunc='mean'
    )

    # Сортируем по максимальному использованию
    pivot_data['max_usage'] = pivot_data.max(axis=1)
    pivot_data = pivot_data.sort_values('max_usage', ascending=False)
    pivot_data = pivot_data.drop('max_usage', axis=1)

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

    fig.update_layout(
        height=700,
        xaxis_title="Дата",
        yaxis_title="Сервер",
        coloraxis_colorbar=dict(
            title="%",
            thickness=20,
            len=0.8
        )
    )

    return fig


def create_cpu_load_chart(df):
    """Создание графика использования памяти"""
    cpu_data = df[df['metric'] == 'cpu.usage.average']

    # Группируем по серверам
    avg_cpu = cpu_data.groupby('vm')['avg_value'].mean().sort_values(ascending=False).reset_index()

    fig = px.bar(
        avg_cpu,
        x='vm',
        y='avg_value',
        title="Среднее использование cpu по серверам",
        labels={'vm': 'Сервер', 'avg_value': 'Использование cpu (%)'},
        color='avg_value',
        color_continuous_scale='Blues'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        xaxis_title="Сервер",
        yaxis_title="Использование cpu (%)",
        coloraxis_colorbar=dict(title="%")
    )

    # Добавляем горизонтальную линию порога
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Критический порог 80%")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Порог низкой нагрузки 30%")

    return fig


def create_memory_load_chart(df):
    """Создание графика использования памяти"""
    mem_data = df[df['metric'] == 'mem.usage.average']

    # Группируем по серверам
    avg_memory = mem_data.groupby('vm')['avg_value'].mean().sort_values(ascending=False).reset_index()

    fig = px.bar(
        avg_memory,
        x='vm',
        y='avg_value',
        title="Среднее использование памяти по серверам",
        labels={'vm': 'Сервер', 'avg_value': 'Использование памяти (%)'},
        color='avg_value',
        color_continuous_scale='Blues'
    )

    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        xaxis_title="Сервер",
        yaxis_title="Использование памяти (%)",
        coloraxis_colorbar=dict(title="%")
    )

    # Добавляем горизонтальную линию порога
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Критический порог 80%")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Порог низкой нагрузки 30%")

    return fig


def create_load_timeline(df, selected_server):
    """Создание таймлайна нагрузки для выбранного сервера"""
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


def create_server_classification_table(df):
    """Создание таблицы классификации серверов"""
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


def main():
    # Заголовок
    st.markdown("<h1 class='main-header'>Дашборд мониторинга нагрузки серверов</h1>", unsafe_allow_html=True)

    # Загрузка данных
    with st.spinner('Загрузка и анализ данных...'):
        df = load_and_prepare_data()
        metrics = create_summary_metrics(df)

    # Боковая панель
    with st.sidebar:
        st.header("Фильтры и настройки")

        # Выбор сервера для детального анализа
        servers = sorted(df['vm'].unique())
        selected_server = st.selectbox(
            "Выберите сервер для детального анализа:",
            servers,
            index=0
        )

    # Основной контент
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card", style="color: black;">
            <h3>Всего серверов</h3>
            <h1>{metrics['total_servers']}</h1>
            <p><strong>Период: {metrics['period']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card", style="color: black;">
            <h3>Нагрузка CPU</h3>
            <p>🟢 Низкая: <strong>{metrics['cpu_low']}</strong> серверов</p>
            <p>🟡 Нормальная: <strong>{metrics['cpu_normal']}</strong> серверов</p>
            <p>🔴 Высокая: <strong>{metrics['cpu_high']}</strong> серверов</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card", style="color: black;">
            <h3>Нагрузка памяти</h3>
            <p>🟢 Низкая: <strong>{metrics['mem_low']}</strong> серверов</p>
            <p>🟡 Нормальная: <strong>{metrics['mem_normal']}</strong> серверов</p>
            <p>🔴 Высокая: <strong>{metrics['mem_high']}</strong> серверов</p>
        </div>
        """, unsafe_allow_html=True)

    # Таблица классификации всех серверов
    st.markdown("---")
    st.header("Классификация всех серверов")

    classification_table = create_server_classification_table(df)
    st.dataframe(
        classification_table,
        use_container_width=True,
        hide_index=True
    )

    # Визуализации
    st.markdown("---")
    st.header("Визуализация нагрузки")


    st.subheader("Тепловая карта нагрузки CPU")
    fig_heatmap = create_cpu_heatmap(df)
    st.plotly_chart(fig_heatmap, use_container_width=True)


    st.subheader("Использование CPU")
    fig_chart = create_cpu_load_chart(df)
    st.plotly_chart(fig_chart, use_container_width=True)


    st.subheader("Тепловая карта нагрузки по памяти")
    fig_heatmap = create_memory_heatmap(df)
    st.plotly_chart(fig_heatmap, use_container_width=True)


    st.subheader("Использование памяти")
    fig_chart = create_memory_load_chart(df)
    st.plotly_chart(fig_chart, use_container_width=True)

    # Детальный анализ выбранного сервера
    st.markdown("---")
    st.header(f"Детальный анализ сервера: {selected_server}")

    col4, col5 = st.columns(2)

    with col4:
        # Основные метрики сервера
        server_data = df[df['vm'] == selected_server]

        avg_cpu = server_data[server_data['metric'] == 'cpu.usage.average']['avg_value'].mean()
        avg_mem = server_data[server_data['metric'] == 'mem.usage.average']['avg_value'].mean()

        # Определяем статус
        cpu_status = "🟢 Низкая" if avg_cpu < 20 else ("🔴 Высокая" if avg_cpu > 70 else "🟡 Нормальная")
        mem_status = "🟢 Низкая" if avg_mem < 30 else ("🔴 Высокая" if avg_mem > 80 else "🟡 Нормальная")

        st.markdown(f"""
        <div class="metric-card", style="color: black;">
            <h3>Средние значения</h3>
            <p><strong>CPU:</strong> {avg_cpu:.2f}% - {cpu_status}</p>
            <p><strong>Память:</strong> {avg_mem:.2f}% - {mem_status}</p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        # Рекомендации
        if '🔴' in cpu_status:
            recommendation = "⚠️ Требуется немедленное вмешательство - высокая CPU нагрузка!"
            card_class = "warning-card"
        elif '🟢' in cpu_status and '🟢' in mem_status:
            recommendation = "✅ Сервер недогружен - возможна консолидация"
            card_class = "success-card"
        else:
            recommendation = "✅ Сервер работает в нормальном режиме"
            card_class = "success-card"

        st.markdown(f"""
        <div class="{card_class}", style="color: black;">
            <h3>Рекомендация</h3>
            <p>{recommendation}</p>
        </div>
        """, unsafe_allow_html=True)

    # Таймлайн нагрузки
    st.subheader("Динамика нагрузки по времени")
    fig_timeline = create_load_timeline(df, selected_server)
    st.plotly_chart(fig_timeline, use_container_width=True)


if __name__ == "__main__":
    main()