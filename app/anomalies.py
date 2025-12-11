import streamlit as st
from llm import call_ai_analysis
import requests

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_statistical_anomalies(df, server_name=None):
    """
    Обнаружение статистических аномалий
    """
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


def get_server_context(df, server_name=None):
    """
    Получение контекста для анализа
    """
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
    """
    Создание секции для обнаружения аномалий
    """
    col1, col2 = st.columns([3, 1])

    with col1:
        # Выбор сервера для анализа
        servers = sorted(df['vm'].unique())
        selected_server = st.selectbox(
            "Выберите сервер для детального анализа:",
            servers,
            index=0 if not st.session_state.anomaly_server else servers.index(st.session_state.anomaly_server)
        )

        # Текстовое поле для вопроса
        question = st.text_input(
            "Задайте вопрос по метрикам:",
            value=f"Проанализируй сервер {selected_server}?" if not st.session_state.anomaly_server
            else f"Есть ли аномалии у {st.session_state.anomaly_server}?",
            placeholder=f"Например: «Проанализируй сервер {selected_server}?»"
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        # Кнопка поиска аномалий
        if st.button("Запустить", type="secondary", use_container_width=True):
            st.session_state.anomaly_mode = True
            st.session_state.anomaly_server = selected_server
            st.session_state.anomaly_response = None
            st.rerun()

    # Если режим анализа аномалий активен
    if st.session_state.anomaly_mode and st.session_state.anomaly_server:
        st.markdown("---")
        st.subheader(f"Анализ для сервера: {st.session_state.anomaly_server}")

        with st.spinner("Анализируем метрики..."):
            # Получаем контекст для анализа
            context = get_server_context(df, st.session_state.anomaly_server)

            # Отображаем статистические аномалии
            anomalies = context['statistical_anomalies']

            if anomalies:
                st.markdown('<div class="anomaly-card">', unsafe_allow_html=True)
                st.subheader("Обнаруженные статистические аномалии:")

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
            st.subheader("AI Анализ")

            if st.session_state.anomaly_response is None:
                # Генерируем AI ответ
                ai_response = call_ai_analysis(context)
                st.session_state.anomaly_response = ai_response

            # Отображаем AI ответ
            st.markdown('<div class="ai-response">', unsafe_allow_html=True)
            st.write(st.session_state.anomaly_response)
            st.markdown('</div>', unsafe_allow_html=True)

        # Кнопка для возврата
        col_back, col_link = st.columns([1, 1])
        with col_back:
            if st.button("← Вернуться к дашборду", type="primary", use_container_width=True):
                st.session_state.anomaly_mode = False
                st.session_state.anomaly_server = None
                st.session_state.anomaly_response = None
                st.rerun()

        with col_link:
            # Проверяем доступность контейнера Llama
            LLAMA_UI_URL_HEALTH = "http://llama-server:8080"
            LLAMA_UI_URL = "http://localhost:8080"

            # Функция для проверки доступности (выполняется на сервере)
            @st.cache_data(ttl=30)  # Кэшируем результат на 30 секунд
            def check_llama_availability():
                try:
                    response = requests.get(f"{LLAMA_UI_URL_HEALTH}/health", timeout=5)
                    return response.status_code == 200
                except requests.exceptions.RequestException:
                    try:
                        response = requests.get(f"{LLAMA_UI_URL}", timeout=5)
                        return response.status_code == 200
                    except:
                        return False

            # В основном коде
            is_available = check_llama_availability()

            if is_available:
                st.link_button(
                    "🚀 Перейти в LLM UI",
                    LLAMA_UI_URL,
                    type="secondary",
                    use_container_width=True,
                    help="Откроет интерфейс LLM в новой вкладке"
                )
            else:
                st.warning("⚠️ LLM UI недоступен")
                if st.button("🔄 Проверить снова"):
                    st.cache_data.clear()  # Очищаем кэш
                    st.rerun()
