import pandas as pd
import streamlit as st
import warnings
from cpu import create_cpu_heatmap, create_cpu_load_chart
from mem import create_memory_heatmap, create_memory_load_chart
from table import create_load_timeline, create_server_classification_table, create_summary_metrics
from anomalies import create_anomaly_detection_section, detect_statistical_anomalies
import os
from dotenv import load_dotenv
from auth import require_auth, get_current_user, has_role
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

# Инициализация состояния сессии для аутентификации
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'role' not in st.session_state:
    st.session_state.role = None

# Инициализация состояния сессии для аномалий
if 'anomaly_mode' not in st.session_state:
    st.session_state.anomaly_mode = False
if 'anomaly_server' not in st.session_state:
    st.session_state.anomaly_server = None
if 'anomaly_response' not in st.session_state:
    st.session_state.anomaly_response = None


@st.cache_data(ttl=300)  # Кэш на 5 минут
def load_and_prepare_data(data_source='db', vm=None, start_date=None, end_date=None):
    """
    Загрузка и подготовка данных

    Args:
        data_source: Источник данных ('db' или 'xlsx')
        vm: Фильтр по серверу (опционально)
        start_date: Начальная дата (опционально)
        end_date: Конечная дата (опционально)
    """
    try:
        if data_source == 'db':
            # Чтение данных из базы данных
            from database.repository import get_metrics_from_db
            from datetime import date as date_type

            # Преобразуем даты если нужно
            if start_date and isinstance(start_date, str):
                start_date = pd.to_datetime(start_date).date()
            if end_date and isinstance(end_date, str):
                end_date = pd.to_datetime(end_date).date()

            df = get_metrics_from_db(
                vm=vm,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                st.warning("База данных пуста. Используйте импорт данных из Excel.")
                # Пробуем загрузить из Excel как fallback
                try:
                    df = pd.read_excel("../data/metrics.xlsx")
                    st.info("Загружены данные из Excel файла (fallback)")
                except:
                    return pd.DataFrame()

        elif data_source == 'xlsx':
            # Чтение данных из файла (legacy)
            df = pd.read_excel("../data/metrics.xlsx")
        else:
            st.error(f"Неизвестный источник данных: {data_source}")
            return pd.DataFrame()

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
        error_msg = str(e)
        st.error(f"Ошибка при загрузке данных: {error_msg}")
        logger.error(f"Ошибка загрузки данных: {error_msg}", exc_info=True)

        # Показываем подсказку если ошибка БД
        if data_source == 'db' and 'connection' in error_msg.lower():
            st.info(
                "Совет: Проверьте подключение к базе данных. Используйте 'xlsx' как источник данных для работы без БД.")

        return pd.DataFrame()


@require_auth
def main():
    # Информация о пользователе в заголовке
    user = get_current_user()

    # Заголовок с информацией о пользователе
    col_header1, col_header2, col_header3 = st.columns([4, 1, 1])

    with col_header1:
        st.markdown("<h1 class='main-header'>Дашборд мониторинга нагрузки серверов</h1>", unsafe_allow_html=True)

    with col_header2:
        if user:
            role_badge = {
                "admin": "Админ",
                "user": "Пользователь",
                "viewer": "Наблюдатель"
            }.get(user.get("role", ""), "Гость")

            st.markdown(f"""
            <div class="user-info">
                <strong>{user.get('name', 'Пользователь')}</strong><br>
                <small>{role_badge}</small>
            </div>
            """, unsafe_allow_html=True)

    with col_header3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 Выход", use_container_width=True):
            from auth import logout_user
            logout_user()
            return

    # Выбор источника данных (только для админов) - в sidebar перед загрузкой
    data_source = 'db'  # По умолчанию используем БД

    # Создаем sidebar для выбора источника данных
    with st.sidebar:
        if has_role("admin"):
            st.markdown("### Настройки данных")
            data_source = st.radio(
                "Источник данных:",
                ['db', 'xlsx'],
                index=0,
                help="db - база данных (рекомендуется), xlsx - Excel файл"
            )
            st.markdown("---")

    # Загрузка данных
    with st.spinner('Загрузка и анализ данных...'):
        df = load_and_prepare_data(data_source=data_source)

        if df.empty:
            if data_source == 'db':
                st.error("База данных пуста или недоступна.")
                st.info("Используйте импорт данных из Excel или проверьте подключение к БД.")
            else:
                st.error("Не удалось загрузить данные. Пожалуйста, проверьте файл data/metrics.xlsx")
            return

        metrics = create_summary_metrics(df)

    # Если режим анализа аномалий активен, показываем только секцию аномалий
    if st.session_state.anomaly_mode:
        # Проверка прав для анализа аномалий
        if has_role("viewer"):
            st.warning("У вас недостаточно прав для анализа аномалий. Требуется роль пользователя или администратора.")
            st.session_state.anomaly_mode = False
            st.rerun()
        else:
            create_anomaly_detection_section(df)
            return

    # Боковая панель с учетом ролей
    with st.sidebar:
        # Информация о пользователе
        if user:
            st.markdown(f"### {user.get('full_name', 'Пользователь')}")
            st.markdown(f"**Роль:** {user.get('role', 'Не определена')}")
            st.markdown(f"**Email:** {user.get('email', 'Не указан')}")
            st.markdown("---")

        # Разрешенные действия в зависимости от роли
        user_role = st.session_state.get("role", "viewer")

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

        # Дополнительные опции для админов
        if has_role("admin"):
            st.markdown("---")
            st.markdown("### Администрирование")
            if st.button("Управление пользователями", use_container_width=True):
                st.info("Функция управления пользователями в разработке")

            if st.button("Экспорт данных", use_container_width=True):
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Скачать CSV",
                    data=csv,
                    file_name="server_metrics.csv",
                    mime="text/csv",
                    use_container_width=True
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

    # Секция поиска аномалий (только для пользователей и админов)
    if not has_role("viewer"):
        st.markdown("---")
        col_anomaly1, col_anomaly2 = st.columns([3, 1])

        with col_anomaly1:
            st.markdown("### Быстрый анализ")
            st.markdown(
                "Нажмите кнопку для детального анализа метрик, поиска аномалий и получения рекомендаций с помощью AI")

        with col_anomaly2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Запустить", type="secondary", use_container_width=True):
                st.session_state.anomaly_mode = True
                st.rerun()
    else:
        st.info("👀 Вы находитесь в режиме просмотра. Для анализа аномалий требуются дополнительные права.")

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


def run_app():
    """Основная функция запуска приложения"""
    main()


if __name__ == "__main__":
    load_css()
    run_app()