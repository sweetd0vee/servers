import plotly.express as px


def create_memory_heatmap(df):
    """
    Тепловая карта использования памяти по дням
    """
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


def create_memory_load_chart(df):
    """
    Создание графика использования памяти
    """
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
