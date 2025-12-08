import pandas as pd
import streamlit as st
import warnings
import json
import requests
from cpu import create_cpu_heatmap, create_cpu_load_chart
from mem import create_memory_heatmap, create_memory_load_chart
from server_dashboard import create_load_timeline, create_server_classification_table
import os
from dotenv import load_dotenv

# Загружаем переменные окружения (для API ключей)
load_dotenv()

warnings.filterwarnings('ignore')

# Настройка страницы
st.set_page_config(
    page_title="Дашборд мониторинга серверов",
    page_icon="🖥️",
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
        font-weight: 700;
    }
    .section-header {
        font-size: 1.8rem;
        color: #2D3748;
        margin: 25px 0 15px 0;
        font-weight: 600;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 8px;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #1E3A8A;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        height: 100%;
    }
    .warning-card {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        height: 100%;
    }
    .success-card {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        height: 100%;
    }
    .anomaly-card {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 20px;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        height: 100%;
    }
    .stDataFrame {
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .stPlotlyChart {
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        padding: 10px;
        background-color: white;
    }
    .stButton button {
        background-color: #ffc107;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
        width: 100%;
    }
    .stButton button:hover {
        background-color: #e0a800;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .ai-response {
        background-color: #f8f9fa;
        border-left: 4px solid #17a2b8;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        white-space: pre-wrap;
        font-family: 'Courier New', monospace;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Инициализация состояния сессии для аномалий
if 'anomaly_mode' not in st.session_state:
    st.session_state.anomaly_mode = False
if 'anomaly_server' not in st.session_state:
    st.session_state.anomaly_server = None
if 'anomaly_response' not in st.session_state:
    st.session_state.anomaly_response = None


@st.cache_data
def load_and_prepare_data():
    """Загрузка и подготовка данных"""
    try:
        # Чтение данных из файла
        df = pd.read_excel("data/metrics.xlsx")

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


def detect_statistical_anomalies(df, server_name=None):
    """Обнаружение статистических аномалий"""
    anomalies = []

    if df.empty:
        return anomalies

    # Фильтрация по серверу если указан
    if server_name:
        df = df[df['vm'] == server_name]

    # Группировка по метрикам и дням
    for metric in df['metric'].unique():
        metric_data = df[df['metric'] == metric]

        # Рассчитываем статистики
        mean_val = metric_data['avg_value'].mean()
        std_val = metric_data['avg_value'].std()

        # Если std слишком маленький, пропускаем
        if std_val < 1:
            continue

        # Находим аномалии (значения за пределами 3 сигм)
        anomalies_mask = abs(metric_data['avg_value'] - mean_val) > (3 * std_val)
        anomaly_rows = metric_data[anomalies_mask]

        for _, row in anomaly_rows.iterrows():
            anomalies.append({
                'server': row['vm'],
                'date': row['date'].strftime('%Y-%m-%d'),
                'metric': metric,
                'value': row['avg_value'],
                'mean': mean_val,
                'std': std_val,
                'z_score': (row['avg_value'] - mean_val) / std_val,
                'type': 'statistical_outlier'
            })

    return anomalies


def call_ai_analysis(context):
    """Вызов AI для анализа аномалий"""
    # Здесь можно интегрировать с различными AI API
    # Например: OpenAI GPT, Yandex GPT, Claude и т.д.

    # Пример для OpenAI (нужен API ключ)
    api_key = os.getenv('OPENAI_API_KEY')

    if not api_key:
        # Если нет API ключа, возвращаем локальный анализ
        return local_ai_analysis(context)

    try:
        # Настройки для OpenAI
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        prompt = f"""Ты — SRE-аналитик с опытом работы 10 лет. 
Проанализируй метрики серверов за последние сутки и ответь на вопросы:
1. Есть ли статистические аномалии в данных?
2. Какие серверы требуют внимания и почему?
3. Какие рекомендации можно дать?

Данные метрик:
{json.dumps(context, indent=2, ensure_ascii=False)}

Ответ предоставь в формате:
📊 **Статистический анализ:**
[анализ статистических аномалий]

⚠️ **Проблемные серверы:**
[список проблемных серверов с причинами]

🎯 **Рекомендации:**
[конкретные рекомендации по действиям]

Используй только факты из предоставленных данных."""

        data = {
            "model": "gpt-4",
            "messages": [
                {"role": "system",
                 "content": "Ты опытный SRE-аналитик, специализирующийся на мониторинге инфраструктуры."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            return local_ai_analysis(context)

    except Exception as e:
        st.warning(f"Ошибка при обращении к AI API: {str(e)}")
        return local_ai_analysis(context)


def local_ai_analysis(context):
    """Локальный анализ аномалий без внешнего API"""

    analysis = """📊 **Статистический анализ:**
Проанализированы метрики за последние сутки. 

⚠️ **Проблемные серверы:**
"""

    # Анализ CPU
    high_cpu = [s for s in context['servers']
                if context['servers'][s].get('cpu_avg', 0) > 80]
    if high_cpu:
        analysis += f"\n• Серверы с высокой CPU нагрузкой (>80%): {', '.join(high_cpu)}"

    # Анализ памяти
    high_mem = [s for s in context['servers']
                if context['servers'][s].get('mem_avg', 0) > 85]
    if high_mem:
        analysis += f"\n• Серверы с высокой нагрузкой памяти (>85%): {', '.join(high_mem)}"

    # Проверка на аномальные пики
    anomalies_found = False
    for server in context['servers']:
        if context['servers'][server].get('has_anomalies', False):
            anomalies_found = True
            analysis += f"\n• {server}: обнаружены статистические аномалии в метриках"

    if not (high_cpu or high_mem or anomalies_found):
        analysis += "\n• Критических проблем не обнаружено"

    analysis += "\n\n🎯 **Рекомендации:**"

    if high_cpu:
        analysis += f"\n1. Для серверов {', '.join(high_cpu)} рассмотреть возможность вертикального масштабирования или оптимизации рабочих нагрузок"

    if high_mem:
        analysis += f"\n2. Для серверов {', '.join(high_mem)} проверить утечки памяти и рассмотреть увеличение RAM"

    if not (high_cpu or high_mem):
        analysis += "\n1. Текущая нагрузка серверов находится в пределах нормы"
        analysis += "\n2. Рекомендуется продолжить регулярный мониторинг"

    analysis += "\n3. Для детального анализа рекомендуется проверить логи приложений на проблемных серверах"

    return analysis


def get_server_context(df, server_name=None):
    """Получение контекста для анализа"""
    context = {
        'total_servers': df['vm'].nunique(),
        'period': {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d')
        },
        'servers': {},
        'statistical_anomalies': []
    }

    servers_to_analyze = [server_name] if server_name else df['vm'].unique()[:10]  # Ограничиваем для производительности

    for server in servers_to_analyze:
        server_data = df[df['vm'] == server]

        if server_data.empty:
            continue

        # CPU метрики
        cpu_data = server_data[server_data['metric'].str.contains('cpu.usage', case=False, na=False)]
        cpu_avg = cpu_data['avg_value'].mean() if not cpu_data.empty else 0
        cpu_max = cpu_data['avg_value'].max() if not cpu_data.empty else 0

        # Memory метрики
        mem_data = server_data[server_data['metric'].str.contains('mem.usage', case=False, na=False)]
        mem_avg = mem_data['avg_value'].mean() if not mem_data.empty else 0
        mem_max = mem_data['avg_value'].max() if not mem_data.empty else 0

        # Диск метрики (если есть)
        disk_data = server_data[server_data['metric'].str.contains('disk', case=False, na=False)]
        disk_avg = disk_data['avg_value'].mean() if not disk_data.empty else None

        context['servers'][server] = {
            'cpu_avg': round(cpu_avg, 2),
            'cpu_max': round(cpu_max, 2),
            'mem_avg': round(mem_avg, 2),
            'mem_max': round(mem_max, 2),
            'has_anomalies': False
        }

        if disk_avg is not None:
            context['servers'][server]['disk_avg'] = round(disk_avg, 2)

    # Детекция статистических аномалий
    statistical_anomalies = detect_statistical_anomalies(df, server_name)
    context['statistical_anomalies'] = statistical_anomalies

    # Отмечаем серверы с аномалиями
    for anomaly in statistical_anomalies:
        if anomaly['server'] in context['servers']:
            context['servers'][anomaly['server']]['has_anomalies'] = True

    return context


def create_anomaly_detection_section(df):
    """Создание секции для обнаружения аномалий"""
    st.markdown('<div class="section-header">🔍 Поиск аномалий</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        # Выбор сервера для анализа
        servers = sorted(df['vm'].unique())
        selected_server = st.selectbox(
            "Выберите сервер для детального анализа аномалий:",
            servers,
            index=0 if not st.session_state.anomaly_server else servers.index(st.session_state.anomaly_server)
        )

        # Текстовое поле для вопроса
        question = st.text_input(
            "Задайте вопрос по метрикам:",
            value=f"Есть ли аномалии у {selected_server}?" if not st.session_state.anomaly_server
            else f"Есть ли аномалии у {st.session_state.anomaly_server}?",
            placeholder=f"Например: «Есть ли аномалии у {selected_server}?»"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Кнопка поиска аномалий
        if st.button("🔍 Найти аномалии", type="secondary", use_container_width=True):
            st.session_state.anomaly_mode = True
            st.session_state.anomaly_server = selected_server
            st.session_state.anomaly_response = None
            st.rerun()

    # Если режим анализа аномалий активен
    if st.session_state.anomaly_mode and st.session_state.anomaly_server:
        st.markdown("---")
        st.subheader(f"Анализ аномалий для сервера: {st.session_state.anomaly_server}")

        with st.spinner("🔍 Анализируем метрики и ищем аномалии..."):
            # Получаем контекст для анализа
            context = get_server_context(df, st.session_state.anomaly_server)

            # Отображаем статистические аномалии
            anomalies = context['statistical_anomalies']

            if anomalies:
                st.markdown('<div class="anomaly-card">', unsafe_allow_html=True)
                st.subheader("📈 Обнаруженные статистические аномалии:")

                for anomaly in anomalies:
                    if anomaly['server'] == st.session_state.anomaly_server:
                        st.write(f"""
                        **Дата:** {anomaly['date']}
                        **Метрика:** {anomaly['metric']}
                        **Значение:** {anomaly['value']:.2f}% (среднее: {anomaly['mean']:.2f}%, Z-оценка: {anomaly['z_score']:.2f})
                        """)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.success("✅ Статистических аномалий не обнаружено")

            # AI анализ
            st.subheader("🤖 AI Анализ")

            if st.session_state.anomaly_response is None:
                # Генерируем AI ответ
                ai_response = call_ai_analysis(context)
                st.session_state.anomaly_response = ai_response

            # Отображаем AI ответ
            st.markdown('<div class="ai-response">', unsafe_allow_html=True)
            st.write(st.session_state.anomaly_response)
            st.markdown('</div>', unsafe_allow_html=True)

        # Кнопка для возврата
        if st.button("← Вернуться к дашборду", type="primary"):
            st.session_state.anomaly_mode = False
            st.session_state.anomaly_server = None
            st.session_state.anomaly_response = None
            st.rerun()


def main():
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
        st.header("⚙️ Фильтры и настройки")

        # Кнопка поиска аномалий в сайдбаре
        if st.button("🔍 Найти аномалии", type="secondary", use_container_width=True):
            st.session_state.anomaly_mode = True
            st.rerun()

        st.markdown("---")

        # Выбор сервера для детального анализа
        servers = sorted(df['vm'].unique())
        selected_server = st.selectbox(
            "Выберите сервер для детального анализа:",
            servers,
            index=0
        )

        # Фильтр по дате
        st.markdown("---")
        st.header("📅 Фильтр по дате")

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
        <div class="metric-card">
            <h3>📊 Всего серверов</h3>
            <h1 style="color: #1E3A8A;">{metrics['total_servers']}</h1>
            <p><strong>Период: {metrics['period']}</strong></p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚡ Нагрузка CPU</h3>
            <p>🟢 Низкая: <strong>{metrics['cpu_low']}</strong> серверов</p>
            <p>🟡 Нормальная: <strong>{metrics['cpu_normal']}</strong> серверов</p>
            <p>🔴 Высокая: <strong>{metrics['cpu_high']}</strong> серверов</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>💾 Нагрузка памяти</h3>
            <p>🟢 Низкая: <strong>{metrics['mem_low']}</strong> серверов</p>
            <p>🟡 Нормальная: <strong>{metrics['mem_normal']}</strong> серверов</p>
            <p>🔴 Высокая: <strong>{metrics['mem_high']}</strong> серверов</p>
        </div>
        """, unsafe_allow_html=True)

    # Секция поиска аномалий (краткая версия)
    st.markdown("---")
    col_anomaly1, col_anomaly2 = st.columns([3, 1])

    with col_anomaly1:
        st.markdown("### 🔍 Быстрый поиск аномалий")
        st.markdown("Нажмите кнопку для детального анализа метрик и поиска аномалий с помощью AI")

    with col_anomaly2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 Запустить анализ аномалий", type="secondary", use_container_width=True):
            st.session_state.anomaly_mode = True
            st.rerun()

    # Остальной код дашборда остается без изменений...
    # Таблица классификации всех серверов
    st.markdown("---")
    st.header("📋 Классификация всех серверов")

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