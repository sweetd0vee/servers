import pandas as pd
import streamlit as st
import warnings
from cpu import create_cpu_heatmap, create_cpu_load_chart
from mem import create_memory_heatmap, create_memory_load_chart
from table import create_load_timeline, create_server_classification_table
from anomalies import create_anomaly_detection_section, detect_statistical_anomalies
import os
from dotenv import load_dotenv
from base_logger import logger

# Загружаем переменные окружения (для API ключей)
load_dotenv()


warnings.filterwarnings('ignore')


# Загрузка CSS из файла
def load_css():
    css_path = "assets/styles.css"
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        # Fallback к hardcoded CSS
        st.markdown("""
        <style>
            /* Минимальный CSS на случай отсутствия файла */
            .main-header {
                font-size: 2.5rem;
                color: #1E3A8A;
                text-align: center;
                padding: 20px 0;
            }
        </style>
        """, unsafe_allow_html=True)


# Настройка страницы
st.set_page_config(
    page_title="Дашборд мониторинга серверов",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Инициализация состояния сессии для аномалий
if 'anomaly_mode' not in st.session_state:
    st.session_state.anomaly_mode = False
if 'anomaly_server' not in st.session_state:
    st.session_state.anomaly_server = None
if 'anomaly_response' not in st.session_state:
    st.session_state.anomaly_response = None


@st.cache_data
def load_and_prepare_data(data_source='xlsx'):
    """Загрузка и подготовка данных"""
    try:
        if data_source == 'xlsx':
            # Чтение данных из файла
            df = pd.read_excel("data/metrics.xlsx")
        # elif data_source == 'db':
        #     df = get_data_from_db()

        # Проверка необходимых колонок
        required_columns = ['date', 'vm', 'metric', 'avg_value']
        for col in required_columns:
            if col not in df.columns:
                st.error(f"Отсутствует обязательная колонка: {col}")
                return pd.DataFrame()

        # Преобразование даты
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

        # Удаление строк с некорректными датами
        df = df.dropna(subset=['date'])

        # Создание классификации нагрузки
        def classify_load(value, metric_type):
            if pd.isna(value):
                return 'Нет данных', 'secondary', '#6c757d'

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
        load_categories = []
        metric_groups = []

        for _, row in df.iterrows():
            metric_name = str(row['metric']).lower()

            if 'cpu' in metric_name and 'usage' in metric_name:
                category, _, _ = classify_load(row['avg_value'], 'cpu')
                load_categories.append(category)
                metric_groups.append('CPU')
            elif 'mem' in metric_name and 'usage' in metric_name:
                category, _, _ = classify_load(row['avg_value'], 'mem')
                load_categories.append(category)
                metric_groups.append('Память')
            elif 'disk' in metric_name and 'usage' in metric_name:
                load_categories.append('Нормальная')
                metric_groups.append('Диск')
            elif 'net' in metric_name and 'usage' in metric_name:
                load_categories.append('Нормальная')
                metric_groups.append('Сеть')
            else:
                load_categories.append('Нормальная')
                metric_groups.append('Другое')

        df['load_category'] = load_categories
        df['metric_group'] = metric_groups

        return df

    except FileNotFoundError:
        st.error("Файл data/metrics.xlsx не найден. Пожалуйста, проверьте путь к файлу.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {str(e)}")
        return pd.DataFrame()


def create_summary_metrics(df):
    """Создание карточек с метриками"""
    if df.empty:
        return {
            'total_servers': 0,
            'period': 'Нет данных',
            'cpu_low': 0,
            'cpu_normal': 0,
            'cpu_high': 0,
            'mem_low': 0,
            'mem_normal': 0,
            'mem_high': 0
        }

    # Общие метрики
    total_servers = df['vm'].nunique()
    start_date = df['date'].min().strftime('%d.%m.%Y')
    end_date = df['date'].max().strftime('%d.%m.%Y')

    # Анализ CPU нагрузки
    cpu_data = df[df['metric'].str.contains('cpu.usage', case=False, na=False)].copy()
    if not cpu_data.empty:
        cpu_data['cpu_category'] = cpu_data['avg_value'].apply(
            lambda x: 'Низкая' if x < 20 else ('Высокая' if x > 70 else 'Нормальная')
        )
    else:
        cpu_data['cpu_category'] = 'Нет данных'

    # Анализ Memory нагрузки
    mem_data = df[df['metric'].str.contains('mem.usage', case=False, na=False)].copy()
    if not mem_data.empty:
        mem_data['mem_category'] = mem_data['avg_value'].apply(
            lambda x: 'Низкая' if x < 30 else ('Высокая' if x > 80 else 'Нормальная')
        )
    else:
        mem_data['mem_category'] = 'Нет данных'

    # Подсчет по категориям
    cpu_low = cpu_data[cpu_data['cpu_category'] == 'Низкая']['vm'].nunique()
    cpu_normal = cpu_data[cpu_data['cpu_category'] == 'Нормальная']['vm'].nunique()
    cpu_high = cpu_data[cpu_data['cpu_category'] == 'Высокая']['vm'].nunique()

    mem_low = mem_data[mem_data['mem_category'] == 'Низкая']['vm'].nunique()
    mem_normal = mem_data[mem_data['mem_category'] == 'Нормальная']['vm'].nunique()
    mem_high = mem_data[mem_data['mem_category'] == 'Высокая']['vm'].nunique()

    return {
        'total_servers': total_servers,
        'period': f"{start_date} - {end_date}",
        'cpu_low': cpu_low,
        'cpu_normal': cpu_normal,
        'cpu_high': cpu_high,
        'mem_low': mem_low,
        'mem_normal': mem_normal,
        'mem_high': mem_high
    }


def main():
    load_css()
    # Заголовок
    st.markdown("<h1 class='main-header'>Дашборд мониторинга нагрузки серверов</h1>", unsafe_allow_html=True)

    # Загрузка данных
    with st.spinner('Загрузка и анализ данных...'):
        df = load_and_prepare_data()

        if df.empty:
            st.error("Не удалось загрузить данные. Пожалуйста, проверьте файл data/metrics.xlsx")
            return

        metrics = create_summary_metrics(df)

    # Если режим анализа аномалий активен, показываем только секцию аномалий
    if st.session_state.anomaly_mode:
        create_anomaly_detection_section(df)
        return

    # Боковая панель (только если не в режиме анализа аномалий)
    with st.sidebar:
        # Выбор сервера для детального анализа
        servers = sorted(df['vm'].unique())
        selected_server = st.selectbox(
            "Выберите сервер для детального анализа:",
            servers,
            index=0
        )

        # Фильтр по дате
        st.markdown("---")

        min_date = df['date'].min().date()
        max_date = df['date'].max().date()

        date_range = st.date_input(
            "Выберите период:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]

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
                <p>🟢 Низкая: <strong>{14}</strong> серверов</p>
                <p>🟡 Нормальная: <strong>{5}</strong> серверов</p>
                <p>🔴 Высокая: <strong>{1}</strong> серверов</p>
            </div>
            """, unsafe_allow_html=True)

    with col3:
            st.markdown(f"""
            <div class="metric-card", style="color: black;">
                    <h3>Нагрузка памяти</h3>
                    <p>🟢 Низкая: <strong>{14}</strong> серверов</p>
                    <p>🟡 Нормальная: <strong>{6}</strong> серверов</p>
                    <p>🔴 Высокая: <strong>{0}</strong> серверов</p>
            </div>
            """, unsafe_allow_html=True)

    # Секция поиска аномалий (краткая версия)
    st.markdown("---")
    col_anomaly1, col_anomaly2 = st.columns([3, 1])

    with col_anomaly1:
        st.markdown("### 🔍 Быстрый анализ")
        st.markdown("Нажмите кнопку для детального анализа метрик, поиска аномалий и получения рекомендаций с помощью AI")

    with col_anomaly2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Запустить", type="secondary", use_container_width=True):
            st.session_state.anomaly_mode = True
            st.rerun()

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

    with st.expander("CPU"):
        st.subheader("Тепловая карта нагрузки CPU")
        fig_heatmap = create_cpu_heatmap(df)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        st.subheader("Использование CPU")
        fig_chart = create_cpu_load_chart(df)
        st.plotly_chart(fig_chart, use_container_width=True)

    with st.expander("Память"):
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