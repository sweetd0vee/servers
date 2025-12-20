# Архитектура проекта AIOps Dashboard

## Содержание

1. [Общая архитектура](#общая-архитектура)
2. [Компоненты системы](#компоненты-системы)
3. [Docker инфраструктура](#docker-инфраструктура)
4. [Поток данных](#поток-данных)
5. [Взаимодействие компонентов](#взаимодействие-компонентов)
6. [Схема базы данных](#схема-базы-данных)
7. [Процесс аутентификации](#процесс-аутентификации)
8. [Структура кода](#структура-кода)

---

## Общая архитектура

```mermaid
graph TB
    subgraph "Пользователь"
        User[👤 Пользователь]
    end
    
    subgraph "Внешний доступ"
        Browser[🌐 Браузер]
    end
    
    subgraph "Docker Network: servers-network"
        subgraph "Frontend Layer"
            HTTPD[Apache HTTPD<br/>Reverse Proxy<br/>:80, :443]
        end
        
        subgraph "Application Layer"
            Streamlit[Streamlit Dashboard<br/>vm-dashboard<br/>:8501]
        end
        
        subgraph "AI/ML Layer"
            LLM[LLM Server<br/>llama-server<br/>:8080]
        end
        
        subgraph "Data Layer"
            PostgreSQL[(PostgreSQL<br/>postgres<br/>:5432)]
            Excel[📊 Excel Files<br/>data/metrics.xlsx]
        end
        
        subgraph "Auth Layer"
            Keycloak[Keycloak<br/>OAuth2 Provider]
        end
    end
    
    User --> Browser
    Browser -->|HTTPS/HTTP| HTTPD
    HTTPD -->|Proxy| Streamlit
    Streamlit -->|OAuth2| Keycloak
    Streamlit -->|Read Data| Excel
    Streamlit -->|Read/Write| PostgreSQL
    Streamlit -->|AI Analysis| LLM
    LLM -->|Model Files| Models[GGUF Models<br/>~/docker-share/models]
    
    style User fill:#e1f5ff
    style Browser fill:#e1f5ff
    style HTTPD fill:#fff4e6
    style Streamlit fill:#e8f5e9
    style LLM fill:#f3e5f5
    style PostgreSQL fill:#e3f2fd
    style Excel fill:#fff9c4
    style Keycloak fill:#fce4ec
```

---

## Компоненты системы

```mermaid
graph LR
    subgraph "Frontend Components"
        A1[Streamlit UI]
        A2[Visualization<br/>Plotly Charts]
        A3[Anomaly Detection UI]
    end
    
    subgraph "Business Logic"
        B1[Data Loading]
        B2[Metrics Calculation]
        B3[Classification Logic]
        B4[Anomaly Detection]
    end
    
    subgraph "Data Access"
        C1[Excel Reader]
        C2[Database Connection]
        C3[SQLAlchemy ORM]
    end
    
    subgraph "AI Services"
        D1[LLM API Client]
        D2[Local LLM Server]
        D3[HuggingFace API]
    end
    
    subgraph "Authentication"
        E1[Keycloak Client]
        E2[Token Management]
        E3[Role-Based Access]
    end
    
    A1 --> B1
    A2 --> B2
    A3 --> B4
    B1 --> C1
    B1 --> C2
    B2 --> B3
    B4 --> D1
    D1 --> D2
    D1 --> D3
    A1 --> E1
    E1 --> E2
    E2 --> E3
    
    style A1 fill:#e8f5e9
    style B1 fill:#fff3e0
    style C1 fill:#e3f2fd
    style D1 fill:#f3e5f5
    style E1 fill:#fce4ec
```

---

## Docker инфраструктура

```mermaid
graph TB
    subgraph "Docker Compose Services"
        subgraph "Network: servers-network"
            direction TB
            
            subgraph "Web Layer"
                HTTPD[🌐 httpd-proxy<br/>Apache 2.4<br/>Ports: 80, 443<br/>Memory: Default]
            end
            
            subgraph "Application Layer"
                DASH[📊 vm-dashboard<br/>Streamlit App<br/>Ports: 8501, 8050<br/>Memory: 2GB<br/>CPU: 2 cores]
            end
            
            subgraph "AI Layer"
                LLAMA[🤖 llama-server<br/>llama.cpp<br/>Port: 8080<br/>Memory: 16GB<br/>CPU: 8 cores]
            end
            
            subgraph "Data Layer"
                PG[(🗄️ postgres<br/>PostgreSQL 16.9<br/>Port: 5432<br/>Memory: Default)]
            end
        end
    end
    
    subgraph "External Volumes"
        VOL1[📁 ~/docker-share/models<br/>GGUF Model Files]
        VOL2[📁 ~/docker-share/postgres-data<br/>Database Data]
        VOL3[📁 ~/Work/.../data<br/>Excel Files]
    end
    
    HTTPD -->|Proxy| DASH
    DASH -->|AI Requests| LLAMA
    DASH -->|Database Queries| PG
    LLAMA -->|Read Models| VOL1
    PG -->|Persist Data| VOL2
    DASH -->|Read Data| VOL3
    
    style HTTPD fill:#fff4e6
    style DASH fill:#e8f5e9
    style LLAMA fill:#f3e5f5
    style PG fill:#e3f2fd
    style VOL1 fill:#fff9c4
    style VOL2 fill:#fff9c4
    style VOL3 fill:#fff9c4
```

### Зависимости сервисов

```mermaid
graph TD
    HTTPD -->|depends_on| DASH
    DASH -->|depends_on| LLAMA
    DASH -->|connects_to| PG
    
    style HTTPD fill:#fff4e6
    style DASH fill:#e8f5e9
    style LLAMA fill:#f3e5f5
    style PG fill:#e3f2fd
```

---

## Поток данных

### Текущий поток (Excel-based)

```mermaid
sequenceDiagram
    participant User as 👤 Пользователь
    participant Browser as 🌐 Браузер
    participant HTTPD as Apache HTTPD
    participant Streamlit as Streamlit App
    participant Excel as Excel File
    participant LLM as LLM Server
    participant Keycloak as Keycloak
    
    User->>Browser: Открывает дашборд
    Browser->>HTTPD: HTTPS Request
    HTTPD->>Streamlit: Proxy Request
    Streamlit->>Keycloak: Проверка аутентификации
    Keycloak-->>Streamlit: Token Valid
    Streamlit->>Excel: Чтение metrics.xlsx
    Excel-->>Streamlit: DataFrame
    Streamlit->>Streamlit: Обработка данных
    Streamlit->>Streamlit: Классификация метрик
    Streamlit-->>Browser: HTML Dashboard
    Browser-->>User: Отображение дашборда
    
    User->>Browser: Запрос AI анализа
    Browser->>Streamlit: AI Analysis Request
    Streamlit->>Streamlit: Подготовка контекста
    Streamlit->>LLM: API Request
    LLM-->>Streamlit: AI Response
    Streamlit-->>Browser: AI Analysis
    Browser-->>User: Результаты анализа
```

### Целевой поток (Database-based)

```mermaid
sequenceDiagram
    participant User as 👤 Пользователь
    participant Streamlit as Streamlit App
    participant DB as PostgreSQL
    participant LLM as LLM Server
    
    User->>Streamlit: Запрос данных
    Streamlit->>DB: SQL Query
    DB-->>Streamlit: Metrics Data
    Streamlit->>Streamlit: Обработка
    Streamlit-->>User: Dashboard
    
    User->>Streamlit: AI Analysis
    Streamlit->>DB: Get Server Metrics
    DB-->>Streamlit: Data
    Streamlit->>LLM: Analysis Request
    LLM-->>Streamlit: AI Response
    Streamlit-->>User: Analysis Results
```

---

## Взаимодействие компонентов

```mermaid
graph TB
    subgraph "User Interface"
        UI[Streamlit Dashboard]
    end
    
    subgraph "Application Modules"
        CPU[CPU Module<br/>cpu.py]
        MEM[Memory Module<br/>mem.py]
        TABLE[Table Module<br/>table.py]
        ANOM[Anomalies Module<br/>anomalies.py]
        AUTH[Auth Module<br/>auth.py]
    end
    
    subgraph "Data Sources"
        EXCEL[Excel Files]
        DB[(PostgreSQL)]
    end
    
    subgraph "External Services"
        LLM_SVC[LLM Server]
        KEYCLOAK[Keycloak]
    end
    
    subgraph "Utilities"
        LOGGER[Logger<br/>base_logger.py]
        CONFIG[Config<br/>config.py]
    end
    
    UI --> CPU
    UI --> MEM
    UI --> TABLE
    UI --> ANOM
    UI --> AUTH
    
    CPU --> EXCEL
    CPU --> DB
    MEM --> EXCEL
    MEM --> DB
    TABLE --> EXCEL
    TABLE --> DB
    ANOM --> EXCEL
    ANOM --> DB
    ANOM --> LLM_SVC
    
    AUTH --> KEYCLOAK
    
    CPU --> LOGGER
    MEM --> LOGGER
    TABLE --> LOGGER
    ANOM --> LOGGER
    AUTH --> LOGGER
    
    CPU --> CONFIG
    MEM --> CONFIG
    ANOM --> CONFIG
    
    style UI fill:#e8f5e9
    style CPU fill:#fff3e0
    style MEM fill:#fff3e0
    style TABLE fill:#fff3e0
    style ANOM fill:#fff3e0
    style AUTH fill:#fce4ec
    style EXCEL fill:#fff9c4
    style DB fill:#e3f2fd
    style LLM_SVC fill:#f3e5f5
    style KEYCLOAK fill:#fce4ec
```

---

## Схема базы данных

### ER-диаграмма

```mermaid
erDiagram
    SERVERS ||--o{ SERVER_METRICS : has
    DATA_IMPORT_LOG ||--o{ SERVER_METRICS : imports
    
    SERVERS {
        uuid id PK
        string vm UK
        string hostname
        string ip_address
        timestamp created_at
        timestamp updated_at
    }
    
    SERVER_METRICS {
        uuid id PK
        string vm FK
        date date
        string metric
        decimal max_value
        decimal min_value
        decimal avg_value
        timestamp created_at
        timestamp updated_at
    }
    
    DATA_IMPORT_LOG {
        uuid id PK
        string source_type
        int records_count
        string status
        timestamp imported_at
    }
```

### Схема таблицы server_metrics

```mermaid
classDiagram
    class ServerMetrics {
        +UUID id
        +String vm
        +DateTime date
        +String metric
        +Decimal max_value
        +Decimal min_value
        +Decimal avg_value
        +DateTime created_at
        +DateTime updated_at
        +UniqueConstraint(vm, date, metric)
    }
    
    class Indexes {
        +idx_metrics_vm_date
        +idx_metrics_date
        +idx_metrics_metric
    }
    
    ServerMetrics --> Indexes
```

### Примеры метрик

| metric | Описание | Единица измерения |
|--------|----------|-------------------|
| `cpu.usage.average` | Средняя загрузка CPU | % |
| `mem.usage.average` | Среднее использование памяти | % |
| `disk.usage.average` | Среднее использование диска | KB/s |
| `net.usage.average` | Среднее использование сети | KB/s |

---

## Процесс аутентификации

```mermaid
sequenceDiagram
    participant User as 👤 Пользователь
    participant Streamlit as Streamlit App
    participant Keycloak as Keycloak Server
    participant DB as Session Storage
    
    User->>Streamlit: Доступ к дашборду
    Streamlit->>Streamlit: Проверка session_state
    
    alt Не авторизован
        Streamlit->>User: Показать страницу входа
        User->>Keycloak: Нажатие "Login with Keycloak"
        Keycloak->>User: Форма входа
        User->>Keycloak: Ввод credentials
        Keycloak->>Keycloak: Проверка учетных данных
        Keycloak->>Streamlit: Redirect с authorization code
        Streamlit->>Keycloak: Exchange code for tokens
        Keycloak-->>Streamlit: Access Token + Refresh Token
        Streamlit->>Keycloak: Get User Info
        Keycloak-->>Streamlit: User Info + Roles
        Streamlit->>DB: Сохранение в session_state
        Streamlit->>User: Доступ к дашборду
    else Авторизован
        Streamlit->>Streamlit: Проверка токена
        alt Токен валиден
            Streamlit->>User: Показать дашборд
        else Токен истек
            Streamlit->>Keycloak: Refresh Token
            Keycloak-->>Streamlit: New Access Token
            Streamlit->>User: Показать дашборд
        else Токен невалиден
            Streamlit->>User: Показать страницу входа
        end
    end
```

### Роли и права доступа

```mermaid
graph LR
    subgraph "Roles"
        ADMIN[🔐 Admin]
        USER[👤 User]
        VIEWER[👀 Viewer]
    end
    
    subgraph "Permissions"
        P1[Просмотр дашборда]
        P2[Анализ аномалий]
        P3[Экспорт данных]
        P4[Управление пользователями]
    end
    
    ADMIN --> P1
    ADMIN --> P2
    ADMIN --> P3
    ADMIN --> P4
    
    USER --> P1
    USER --> P2
    USER --> P3
    
    VIEWER --> P1
    
    style ADMIN fill:#ffcdd2
    style USER fill:#c8e6c9
    style VIEWER fill:#fff9c4
```

---

## Структура кода

### Модульная структура

```mermaid
graph TD
    subgraph "app/"
        A1[app.py / app_new.py<br/>Main Application]
        A2[cpu.py<br/>CPU Visualizations]
        A3[mem.py<br/>Memory Visualizations]
        A4[table.py<br/>Table Generation]
        A5[anomalies.py<br/>Anomaly Detection]
        A6[auth.py<br/>Authentication]
        A7[llm.py<br/>LLM Integration]
        A8[config.py<br/>Configuration]
    end
    
    subgraph "database/"
        D1[connection.py<br/>SQLAlchemy]
        D2[database.py<br/>psycopg2]
        D3[table.py<br/>Models]
        D4[db_import.py<br/>Data Import]
        D5[db_export.py<br/>Data Export]
    end
    
    subgraph "docker/"
        DO1[app/<br/>Dockerfile]
        DO2[postgres/<br/>Dockerfile]
        DO3[httpd/<br/>Dockerfile]
        DO4[app/<br/>docker-compose.yaml]
    end
    
    A1 --> A2
    A1 --> A3
    A1 --> A4
    A1 --> A5
    A1 --> A6
    A5 --> A7
    A2 --> A8
    A3 --> A8
    A5 --> A8
    
    A1 --> D1
    A1 --> D2
    D4 --> D1
    D5 --> D1
    
    style A1 fill:#e8f5e9
    style A2 fill:#fff3e0
    style A3 fill:#fff3e0
    style A4 fill:#fff3e0
    style A5 fill:#fff3e0
    style A6 fill:#fce4ec
    style A7 fill:#f3e5f5
    style D1 fill:#e3f2fd
    style D2 fill:#e3f2fd
```

### Зависимости модулей

```mermaid
graph LR
    subgraph "Core"
        MAIN[app_new.py]
        CONFIG[config.py]
        LOGGER[base_logger.py]
    end
    
    subgraph "Visualization"
        CPU[cpu.py]
        MEM[mem.py]
        TABLE[table.py]
    end
    
    subgraph "Features"
        ANOM[anomalies.py]
        AUTH[auth.py]
    end
    
    subgraph "Data"
        DB_CONN[connection.py]
        DB_MODEL[table.py]
    end
    
    subgraph "External"
        LLM[llm.py]
    end
    
    MAIN --> CONFIG
    MAIN --> LOGGER
    MAIN --> CPU
    MAIN --> MEM
    MAIN --> TABLE
    MAIN --> ANOM
    MAIN --> AUTH
    
    CPU --> CONFIG
    CPU --> LOGGER
    MEM --> CONFIG
    MEM --> LOGGER
    TABLE --> LOGGER
    ANOM --> LLM
    ANOM --> LOGGER
    AUTH --> LOGGER
    
    MAIN --> DB_CONN
    DB_CONN --> DB_MODEL
    
    style MAIN fill:#e8f5e9
    style CONFIG fill:#fff9c4
    style LOGGER fill:#fff9c4
```

---

## Поток обработки данных

### Процесс загрузки и обработки

```mermaid
flowchart TD
    START([Запуск приложения]) --> AUTH_CHECK{Проверка<br/>аутентификации}
    AUTH_CHECK -->|Не авторизован| LOGIN[Страница входа]
    AUTH_CHECK -->|Авторизован| LOAD_DATA[Загрузка данных]
    
    LOGIN --> KEYCLOAK[Keycloak OAuth2]
    KEYCLOAK --> AUTH_CHECK
    
    LOAD_DATA --> DATA_SOURCE{Источник данных}
    DATA_SOURCE -->|Excel| READ_EXCEL[Чтение Excel файла]
    DATA_SOURCE -->|Database| QUERY_DB[SQL запрос к БД]
    
    READ_EXCEL --> VALIDATE[Валидация данных]
    QUERY_DB --> VALIDATE
    
    VALIDATE --> PROCESS[Обработка данных]
    PROCESS --> CLASSIFY[Классификация метрик]
    CLASSIFY --> CALCULATE[Расчет статистики]
    CALCULATE --> CACHE[Кэширование]
    CACHE --> DISPLAY[Отображение дашборда]
    
    DISPLAY --> USER_INTERACTION{Действие пользователя}
    USER_INTERACTION -->|Выбор сервера| SERVER_DETAIL[Детальный анализ]
    USER_INTERACTION -->|Анализ аномалий| ANOMALY_DETECT[Детекция аномалий]
    USER_INTERACTION -->|Фильтр дат| FILTER[Фильтрация]
    
    ANOMALY_DETECT --> STAT_ANOMALY[Статистические аномалии]
    ANOMALY_DETECT --> AI_ANALYSIS[AI анализ]
    AI_ANALYSIS --> LLM_CALL[Запрос к LLM]
    LLM_CALL --> AI_RESPONSE[AI ответ]
    AI_RESPONSE --> DISPLAY
    
    SERVER_DETAIL --> DISPLAY
    FILTER --> PROCESS
    
    style START fill:#e1f5ff
    style AUTH_CHECK fill:#fff9c4
    style LOAD_DATA fill:#e8f5e9
    style AI_ANALYSIS fill:#f3e5f5
    style DISPLAY fill:#c8e6c9
```

---

## Интеграция с LLM

### Стратегия fallback

```mermaid
graph TD
    START[Запрос AI анализа] --> PREPARE[Подготовка контекста]
    PREPARE --> TRY_LOCAL{Попытка 1:<br/>Локальный LLM}
    
    TRY_LOCAL -->|Доступен| LOCAL_LLM[llama-server:8080]
    TRY_LOCAL -->|Недоступен| TRY_HF{Попытка 2:<br/>HuggingFace API}
    
    TRY_HF -->|Доступен| HF_API1[HuggingFace Model 1]
    TRY_HF -->|Недоступен| TRY_HF2{Попытка 3:<br/>Fallback Model}
    
    TRY_HF2 -->|Доступен| HF_API2[HuggingFace Model 2]
    TRY_HF2 -->|Недоступен| RULE_BASED[Rule-based Analysis]
    
    LOCAL_LLM --> SUCCESS[Успешный ответ]
    HF_API1 --> SUCCESS
    HF_API2 --> SUCCESS
    RULE_BASED --> SUCCESS
    
    SUCCESS --> RETURN[Возврат результата]
    
    style START fill:#e1f5ff
    style LOCAL_LLM fill:#f3e5f5
    style HF_API1 fill:#fff3e0
    style HF_API2 fill:#fff3e0
    style RULE_BASED fill:#ffcdd2
    style SUCCESS fill:#c8e6c9
```

---

## Схема развертывания

### Production Deployment

```mermaid
graph TB
    subgraph "Production Environment"
        subgraph "Load Balancer"
            LB[Load Balancer<br/>nginx/HAProxy]
        end
        
        subgraph "Application Cluster"
            APP1[Streamlit Instance 1]
            APP2[Streamlit Instance 2]
            APP3[Streamlit Instance N]
        end
        
        subgraph "Database Cluster"
            PG_MASTER[(PostgreSQL Master)]
            PG_REPLICA[(PostgreSQL Replica)]
        end
        
        subgraph "AI Services"
            LLM1[LLM Server 1]
            LLM2[LLM Server 2]
        end
        
        subgraph "Auth Service"
            KEYCLOAK[Keycloak Cluster]
        end
        
        subgraph "Storage"
            VOL[Persistent Volumes]
        end
    end
    
    LB --> APP1
    LB --> APP2
    LB --> APP3
    
    APP1 --> PG_MASTER
    APP2 --> PG_MASTER
    APP3 --> PG_MASTER
    
    PG_MASTER --> PG_REPLICA
    
    APP1 --> LLM1
    APP2 --> LLM2
    APP3 --> LLM1
    
    APP1 --> KEYCLOAK
    APP2 --> KEYCLOAK
    APP3 --> KEYCLOAK
    
    PG_MASTER --> VOL
    PG_REPLICA --> VOL
    
    style LB fill:#fff4e6
    style APP1 fill:#e8f5e9
    style APP2 fill:#e8f5e9
    style APP3 fill:#e8f5e9
    style PG_MASTER fill:#e3f2fd
    style PG_REPLICA fill:#e3f2fd
    style LLM1 fill:#f3e5f5
    style LLM2 fill:#f3e5f5
    style KEYCLOAK fill:#fce4ec
```

---

## Технические характеристики

### Ресурсы контейнеров

| Сервис | CPU | Memory | Порты | Описание |
|--------|-----|--------|-------|----------|
| `vm-dashboard` | 2 cores | 2 GB | 8501, 8050 | Streamlit приложение |
| `llama-server` | 8 cores | 16 GB | 8080 | LLM inference сервер |
| `postgres` | Default | Default | 5432 | База данных |
| `httpd-proxy` | Default | Default | 80, 443 | Reverse proxy |

### Порты и endpoints

| Сервис | Порт | Endpoint | Описание |
|--------|------|----------|----------|
| HTTPD | 80 | `/` | HTTP (redirect to HTTPS) |
| HTTPD | 443 | `/dashboard` | HTTPS proxy to Streamlit |
| Streamlit | 8501 | `/` | Main dashboard |
| LLM Server | 8080 | `/completion` | LLM API |
| PostgreSQL | 5432 | - | Database connection |

---

## Легенда диаграмм

### Цветовая схема

- 🟢 **Зеленый** - Application/UI компоненты
- 🟡 **Желтый** - Configuration/Utilities
- 🔵 **Синий** - Data/Database компоненты
- 🟣 **Фиолетовый** - AI/ML компоненты
- 🔴 **Красный** - Authentication/Security
- 🟠 **Оранжевый** - Infrastructure/Network

### Символы

- 👤 - Пользователь
- 🌐 - Веб-браузер
- 📊 - Данные/Файлы
- 🗄️ - База данных
- 🤖 - AI/ML сервис
- 🔐 - Аутентификация
- 📁 - Хранилище/Volumes

---

**Дата создания:** Январь 2025  
**Версия:** 1.0  
**Статус:** Текущая архитектура (с рекомендациями по улучшению)

