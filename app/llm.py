"""
Единый класс для анализа метрик серверов с использованием различных LLM провайдеров.

Поддерживаемые провайдеры:
- hf_api: Hugging Face Inference API (внешний сервис)
- local: Локальная модель через transformers (Qwen/Qwen2.5-3B-Instruct)
- rule_based: Анализ на основе правил (fallback)
- auto: Автоматический выбор с fallback цепочкой (по умолчанию)

Примеры использования:

1. Простое использование (автоматический выбор провайдера):
    from app.llm import call_ai_analysis

    context = {
        'servers': {
            'server1': {'cpu_avg': 85, 'mem_avg': 70, 'has_anomalies': True}
        }
    }
    analysis = call_ai_analysis(context)

2. Использование класса напрямую:
    from app.llm import ServerMetricsAnalyzer

    analyzer = ServerMetricsAnalyzer(provider="local")
    result = analyzer.analyze(context)

    # Или для текстового запроса:
    result = analyzer.analyze_query("CPU: 85%, RAM: 70%")

3. Настройка через переменные окружения:
    export LLM_PROVIDER=local
    export LLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct
    export HF_API_KEY=your_api_key_here

4. Использование singleton:
    from app.llm import get_analyzer

    analyzer = get_analyzer()  # Использует настройки из env
    result = analyzer.analyze(context)
"""
import os
import re
import requests
from typing import Dict, Any, Optional, Union
import logging

# Попытка импортировать streamlit (может быть недоступен вне Streamlit окружения)
try:
    import streamlit as st

    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Логирование
logger = logging.getLogger(__name__)

# Попытка импортировать transformers (может быть недоступен)
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers не установлен, локальная модель недоступна")


class ServerMetricsAnalyzer:
    """
    Единый анализатор метрик серверов с поддержкой различных провайдеров LLM.

    Args:
        provider: Провайдер для анализа. Варианты:
            - "hf_api": Hugging Face Inference API
            - "local": Локальная модель через transformers
            - "rule_based": Анализ на основе правил
            - "auto": Автоматический выбор с fallback (по умолчанию)
        model_name: Имя модели для локального провайдера (по умолчанию Qwen/Qwen2.5-3B-Instruct)
        hf_api_key: API ключ для Hugging Face (если не указан, берется из env)
    """

    # Конфигурация по умолчанию
    DEFAULT_MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"
    DEFAULT_TIMEOUT = 90
    DEFAULT_MAX_TOKENS = 400

    # Список моделей Hugging Face для попыток (от легких к тяжелым)
    HF_MODELS = [
        {
            "url": "https://api-inference.huggingface.co/models/sshleifer/tiny-gpt2",
            "name": "TinyGPT2",
            "tokens": 300
        },
        {
            "url": "https://api-inference.huggingface.co/models/google/flan-t5-small",
            "name": "Flan-T5-Small",
            "tokens": 400
        },
        {
            "url": "https://api-inference.huggingface.co/models/EleutherAI/gpt-neo-125m",
            "name": "GPT-Neo-125M",
            "tokens": 500
        },
        {
            "url": "https://api-inference.huggingface.co/models/distilgpt2",
            "name": "DistilGPT2",
            "tokens": 500
        },
        {
            "url": "https://api-inference.huggingface.co/models/microsoft/phi-2",
            "name": "Phi-2",
            "tokens": 700
        }
    ]

    def __init__(
            self,
            provider: str = "auto",
            model_name: Optional[str] = None,
            hf_api_key: Optional[str] = None
    ):
        """
        Инициализация анализатора.

        Args:
            provider: Провайдер для анализа ("auto", "hf_api", "local", "rule_based")
            model_name: Имя модели для локального провайдера
            hf_api_key: API ключ для Hugging Face
        """
        self.provider = provider.lower()
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.hf_api_key = hf_api_key or os.getenv("HF_API_KEY")

        # Для локального провайдера
        self.model = None
        self.tokenizer = None
        self.device = None

        # Определяем устройство для локальной модели
        if TRANSFORMERS_AVAILABLE:
            self.device = self._get_device()
            logger.info(f"Определено устройство: {self.device}")

        # Проверяем доступность провайдеров
        self._check_provider_availability()

    def _get_device(self) -> str:
        """Определяет лучшее доступное устройство для локальной модели."""
        if not TRANSFORMERS_AVAILABLE:
            return "cpu"

        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _check_provider_availability(self):
        """Проверяет доступность выбранного провайдера."""
        if self.provider == "local" and not TRANSFORMERS_AVAILABLE:
            logger.warning("Локальный провайдер недоступен (transformers не установлен), переключаемся на rule_based")
            self.provider = "rule_based"

        if self.provider == "hf_api" and not self.hf_api_key:
            logger.warning("HF API ключ не найден, переключаемся на rule_based")
            self.provider = "rule_based"

    def analyze(self, context: Union[Dict[str, Any], str]) -> str:
        """
        Основной метод анализа метрик.

        Args:
            context: Контекст для анализа. Может быть:
                - Dict с метриками серверов (как в anomalies.py)
                - str с текстовым запросом

        Returns:
            Текст анализа метрик
        """
        # Определяем тип входных данных
        if isinstance(context, str):
            return self.analyze_query(context)

        # Для dict контекста используем выбранный провайдер
        if self.provider == "auto":
            return self._analyze_with_fallback(context)
        elif self.provider == "hf_api":
            return self._analyze_hf_api(context)
        elif self.provider == "local":
            return self._analyze_local(context)
        elif self.provider == "rule_based":
            return self._analyze_rule_based(context)
        else:
            logger.warning(f"Неизвестный провайдер: {self.provider}, используем rule_based")
            return self._analyze_rule_based(context)

    def analyze_query(self, query: str) -> str:
        """
        Анализ текстового запроса.

        Args:
            query: Текстовый запрос с метриками

        Returns:
            Текст анализа
        """
        # Парсим метрики из запроса
        metrics = self._parse_metrics_from_query(query)

        # Создаем контекст из метрик
        context = {
            'query': query,
            'metrics': metrics
        }

        return self.analyze(context)

    def _analyze_with_fallback(self, context: Dict[str, Any]) -> str:
        """
        Анализ с автоматическим fallback через цепочку провайдеров.

        Порядок попыток:
        1. Hugging Face API (если доступен ключ)
        2. Локальная модель (если transformers доступен)
        3. Rule-based анализ (всегда доступен)
        """
        # Попытка 1: Hugging Face API
        if self.hf_api_key:
            try:
                logger.info("Попытка анализа через Hugging Face API")
                result = self._analyze_hf_api(context)
                if result and len(result) > 50:  # Проверяем что получили осмысленный ответ
                    return result
            except Exception as e:
                logger.warning(f"HF API недоступен: {e}")

        # Попытка 2: Локальная модель
        if TRANSFORMERS_AVAILABLE:
            try:
                logger.info("Попытка анализа через локальную модель")
                result = self._analyze_local(context)
                if result and len(result) > 50:
                    return result
            except Exception as e:
                logger.warning(f"Локальная модель недоступна: {e}")

        # Fallback: Rule-based анализ
        logger.info("Используется rule-based анализ")
        return self._analyze_rule_based(context)

    def _analyze_hf_api(self, context: Dict[str, Any]) -> str:
        """
        Анализ через Hugging Face Inference API.

        Args:
            context: Контекст с метриками

        Returns:
            Текст анализа
        """
        if not self.hf_api_key:
            raise ValueError("HF API ключ не установлен")

        prompt = self._prepare_prompt_from_context(context)

        headers = {
            "Authorization": f"Bearer {self.hf_api_key}",
            "Content-Type": "application/json"
        }

        # Пробуем модели по порядку
        for model_config in self.HF_MODELS:
            try:
                data = {
                    "inputs": prompt[:800],  # Ограничиваем длину
                    "parameters": {
                        "max_new_tokens": model_config["tokens"],
                        "temperature": 0.3,
                        "return_full_text": False
                    }
                }

                response = requests.post(
                    model_config["url"],
                    headers=headers,
                    json=data,
                    timeout=self.DEFAULT_TIMEOUT
                )

                if response.status_code == 200:
                    result = response.json()
                    analysis = self._extract_text_from_hf_response(result)
                    if analysis:
                        return f"Анализ (модель: {model_config['name']}):\n\n{analysis}"

            except Exception as e:
                logger.debug(f"Модель {model_config['name']} недоступна: {e}")
                continue

        raise Exception("Все модели Hugging Face недоступны")

    def _analyze_local(self, context: Dict[str, Any]) -> str:
        """
        Анализ через локальную модель transformers.

        Args:
            context: Контекст с метриками

        Returns:
            Текст анализа
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers не установлен")

        # Загружаем модель при первом использовании
        if self.model is None:
            self._load_local_model()

        if self.model is None:
            raise RuntimeError("Не удалось загрузить локальную модель")

        prompt = self._prepare_prompt_from_context(context)

        try:
            # Генерируем ответ
            if isinstance(self.model, pipeline):
                # Pipeline подход
                response = self.model(
                    prompt,
                    max_length=500,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    num_return_sequences=1
                )[0]['generated_text']
            else:
                # Прямая работа с моделью
                inputs = self.tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512
                )

                # Переносим на устройство
                if self.device in ["cuda", "mps"]:
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=self.DEFAULT_MAX_TOKENS,
                        temperature=0.7,
                        do_sample=True,
                        top_p=0.9,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id
                    )

                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Извлекаем только новую часть ответа
            if prompt in response:
                response = response[len(prompt):].strip()

            # Очищаем ответ
            response = self._clean_response(response)

            return response

        except Exception as e:
            logger.error(f"Ошибка генерации локальной модели: {e}")
            raise

    def _load_local_model(self):
        """Загружает локальную модель transformers."""
        try:
            logger.info(f"Загрузка локальной модели: {self.model_name}")

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                padding_side="left"
            )

            # Устанавливаем pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Определяем dtype
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

            # Загружаем модель
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
                device_map="auto" if self.device == "cuda" else None,
                low_cpu_mem_usage=True
            )

            # Для MPS переносим вручную
            if self.device == "mps":
                self.model.to("mps")

            logger.info(f"Модель {self.model_name} успешно загружена")

        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            # Пробуем fallback через pipeline
            try:
                logger.info("Попытка загрузки через pipeline")
                self.model = pipeline(
                    "text-generation",
                    model=self.model_name,
                    device=self.device if self.device != "mps" else -1,
                    max_length=200
                )
                logger.info("Модель загружена через pipeline")
            except Exception as e2:
                logger.error(f"Не удалось загрузить модель: {e2}")
                self.model = None

    def _analyze_rule_based(self, context: Dict[str, Any]) -> str:
        """
        Анализ на основе правил (fallback).

        Args:
            context: Контекст с метриками

        Returns:
            Текст анализа
        """
        metrics = self._extract_metrics_from_context(context)

        analysis = []
        recommendations = []
        priorities = []

        # Анализ CPU
        cpu = metrics.get('cpu')
        if cpu is not None:
            if cpu > 90:
                analysis.append("🔴 Критическая загрузка CPU")
                recommendations.append("Срочно проверьте процессы, найдите утечки")
                priorities.append("1. Анализ процессов, убить тяжелые")
            elif cpu > 70:
                analysis.append("🟡 Высокая загрузка CPU")
                recommendations.append("Оптимизируйте код, добавьте кэширование")
                priorities.append("1. Оптимизация запросов")
            else:
                analysis.append("✅ CPU в норме")

        # Анализ RAM
        ram = metrics.get('ram') or metrics.get('mem')
        if ram is not None:
            if ram > 90:
                analysis.append("🔴 Критическая загрузка памяти")
                recommendations.append("Увеличьте RAM или настройте swap")
                priorities.append("2. Увеличение памяти")
            elif ram > 75:
                analysis.append("🟡 Высокая загрузка памяти")
                recommendations.append("Проверьте утечки памяти")
                priorities.append("2. Мониторинг памяти")
            else:
                analysis.append("✅ Память в норме")

        # Анализ Disk
        disk = metrics.get('disk')
        if disk is not None:
            if disk > 95:
                analysis.append("🔴 Диск почти заполнен")
                recommendations.append("Срочно очистите место")
                priorities.append("3. Очистка диска")
            elif disk > 80:
                analysis.append("🟡 Мало места на диске")
                recommendations.append("Удалите старые логи и временные файлы")
                priorities.append("3. Оптимизация хранения")
            else:
                analysis.append("✅ Диск в норме")

        # Анализ серверов из контекста
        if 'servers' in context:
            servers = context['servers']
            for server_name, server_data in servers.items():
                if server_data.get('has_anomalies'):
                    cpu_avg = server_data.get('cpu_avg', 0)
                    mem_avg = server_data.get('mem_avg', 0)
                    analysis.append(f"⚠️ Сервер {server_name}: CPU={cpu_avg}%, RAM={mem_avg}%")

        # Статистические аномалии
        if 'statistical_anomalies' in context and context['statistical_anomalies']:
            anomalies_count = len(context['statistical_anomalies'])
            analysis.append(f"📊 Обнаружено {anomalies_count} статистических аномалий")
            recommendations.append("Проверьте серверы с аномалиями в деталях")

        # Если нет конкретных метрик, даем общий совет
        if not analysis:
            percentages = metrics.get('percentages', [])
            if percentages:
                avg_percent = sum(percentages) / len(percentages)
                if avg_percent > 80:
                    analysis.append("⚠️ Высокая общая нагрузка")
                    recommendations.append("Рекомендуется полный аудит системы")
                else:
                    analysis.append("✅ Нагрузка в допустимых пределах")
            else:
                analysis.append("ℹ️ Не удалось точно проанализировать метрики")
                recommendations.append("Уточните значения CPU, RAM, Disk в процентах")

        # Формируем финальный ответ
        result = []
        if analysis:
            result.append("📊 **АНАЛИЗ:**")
            result.extend([f"- {a}" for a in analysis])

        if recommendations:
            result.append("\n🛠️ **РЕКОМЕНДАЦИИ:**")
            result.extend([f"- {r}" for r in recommendations])

        if priorities:
            result.append("\n🚀 **ПРИОРИТЕТЫ:**")
            result.extend([f"{p}" for p in priorities])

        return '\n'.join(result) if result else "Не удалось проанализировать метрики"

    def _prepare_prompt_from_context(self, context: Dict[str, Any]) -> str:
        """
        Подготавливает промпт из контекста для LLM.

        Args:
            context: Контекст с метриками

        Returns:
            Текст промпта
        """
        # Если есть query, используем его
        if 'query' in context:
            query = context['query']
            return f"""Ты эксперт по системному администрированию. 
Проанализируй метрики сервера и дай конкретные рекомендации.

Запрос: {query}

Формат ответа:
1. Анализ текущего состояния
2. Выявленные проблемы
3. Рекомендации по оптимизации
4. Приоритет действий

Анализ:"""

        # Формируем промпт из структурированных данных
        prompt_parts = ["Ты эксперт по системному администрированию. Проанализируй метрики серверов:\n"]

        if 'servers' in context:
            prompt_parts.append("Метрики серверов:")
            for server_name, server_data in context['servers'].items():
                cpu_avg = server_data.get('cpu_avg', 0)
                mem_avg = server_data.get('mem_avg', 0)
                mem_max = server_data.get('mem_max', 0)
                cpu_max = server_data.get('cpu_max', 0)
                prompt_parts.append(
                    f"- {server_name}: CPU среднее={cpu_avg}%, макс={cpu_max}%, "
                    f"RAM среднее={mem_avg}%, макс={mem_max}%"
                )

        if 'statistical_anomalies' in context and context['statistical_anomalies']:
            prompt_parts.append("\nСтатистические аномалии:")
            for anomaly in context['statistical_anomalies'][:5]:  # Ограничиваем
                prompt_parts.append(
                    f"- {anomaly['server']} ({anomaly['date']}): "
                    f"{anomaly['metric']}={anomaly['value']:.2f}% "
                    f"(Z-score: {anomaly['z_score']:.2f})"
                )

        prompt_parts.append("\nДай структурированный ответ:")
        prompt_parts.append("📊 АНАЛИЗ:")
        prompt_parts.append("⚠️ ПРОБЛЕМЫ:")
        prompt_parts.append("🛠️ РЕКОМЕНДАЦИИ:")
        prompt_parts.append("🚀 ПРИОРИТЕТЫ:")
        prompt_parts.append("\nОтвечай только на русском языке, будь конкретным и практичным.")

        return "\n".join(prompt_parts)

    def _extract_metrics_from_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает метрики из контекста для rule-based анализа.

        Args:
            context: Контекст с метриками

        Returns:
            Словарь с метриками
        """
        metrics = {}

        # Извлекаем из servers
        if 'servers' in context:
            servers = context['servers']
            cpu_values = []
            ram_values = []

            for server_data in servers.values():
                if 'cpu_avg' in server_data:
                    cpu_values.append(server_data['cpu_avg'])
                if 'mem_avg' in server_data:
                    ram_values.append(server_data['mem_avg'])

            if cpu_values:
                metrics['cpu'] = sum(cpu_values) / len(cpu_values)
            if ram_values:
                metrics['ram'] = sum(ram_values) / len(ram_values)

        # Извлекаем из query если есть
        if 'query' in context:
            parsed = self._parse_metrics_from_query(context['query'])
            metrics.update(parsed)

        # Извлекаем из metrics если есть
        if 'metrics' in context:
            metrics.update(context['metrics'])

        return metrics

    def _parse_metrics_from_query(self, query: str) -> Dict[str, Any]:
        """
        Парсит метрики из текстового запроса.

        Args:
            query: Текстовый запрос

        Returns:
            Словарь с метриками
        """
        metrics = {}

        # Парсинг процентов
        percent_matches = re.findall(r'(\d+)\s*%', query)
        if percent_matches:
            metrics['percentages'] = [int(p) for p in percent_matches]

        # Поиск конкретных метрик
        patterns = {
            'cpu': r'(?:cpu|цпу|процессор)[:\s]*(\d+)%?',
            'ram': r'(?:ram|память|memory|mem)[:\s]*(\d+)%?',
            'disk': r'(?:disk|диск)[:\s]*(\d+)%?',
            'network': r'(?:сеть|network)[:\s]*(\d+)%?',
            'requests': r'(\d+)\s*(?:запросов|requests)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                try:
                    metrics[key] = int(match.group(1))
                except:
                    pass

        return metrics

    def _extract_text_from_hf_response(self, data: Any) -> str:
        """
        Извлекает текст из ответа Hugging Face API.

        Args:
            data: Ответ от API

        Returns:
            Текст анализа
        """
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            for key in ['generated_text', 'text', 'output', 'response']:
                if key in data:
                    return str(data[key])
            # Если не нашли ключ, возвращаем первый не-технический ключ
            for key in data:
                if key not in ['error', 'warnings', 'status']:
                    return str(data[key])
            return str(data)
        elif isinstance(data, list) and len(data) > 0:
            return self._extract_text_from_hf_response(data[0])
        return str(data)

    def _clean_response(self, text: str) -> str:
        """
        Очищает ответ модели от мусора.

        Args:
            text: Текст ответа

        Returns:
            Очищенный текст
        """
        # Убираем специальные символы и повторения
        text = re.sub(r'[^\w\s\d%.,!?;:()\-—\n\rа-яА-ЯёЁ]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Ищем структурированные части
        lines = text.split('\n')
        clean_lines = []

        for line in lines:
            line = line.strip()
            if line and len(line) > 3:
                # Убираем строки с бессмысленным содержанием
                if not re.search(r'[^\w\s\d%.,!?;:()\-—а-яА-ЯёЁ]', line[:20]):
                    clean_lines.append(line)

        return '\n'.join(clean_lines[:20])  # Ограничиваем длину


# Глобальный экземпляр для обратной совместимости
_global_analyzer = None


def get_analyzer(provider: str = None) -> ServerMetricsAnalyzer:
    """
    Получает глобальный экземпляр анализатора (singleton pattern).

    Args:
        provider: Провайдер (если None, используется из env или "auto")

    Returns:
        Экземпляр ServerMetricsAnalyzer
    """
    global _global_analyzer

    if _global_analyzer is None or (provider and _global_analyzer.provider != provider):
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "auto")

        _global_analyzer = ServerMetricsAnalyzer(provider=provider)

    return _global_analyzer


# Функции для обратной совместимости
def call_ai_analysis(context: Union[Dict[str, Any], str]) -> str:
    """
    Функция для обратной совместимости с существующим кодом.

    Args:
        context: Контекст для анализа

    Returns:
        Текст анализа
    """
    analyzer = get_analyzer()
    return analyzer.analyze(context)


def analyze_server_metrics(query: str, use_simple: bool = True) -> str:
    """
    Функция для обратной совместимости с существующим кодом.

    Args:
        query: Текстовый запрос с метриками
        use_simple: Игнорируется (для совместимости)

    Returns:
        Текст анализа
    """
    analyzer = get_analyzer()
    return analyzer.analyze_query(query)


def local_ai_analysis(context):
    """Локальный анализ при недоступности API"""
    # Упрощенный локальный анализ
    analysis_result = """**Статистический анализ:**
Проведен базовый анализ метрик. Для детального анализа требуется подключение к AI API.

⚠️ **Проблемные серверы:**
Рекомендуется проверить серверы с пиковыми значениями CPU > 80% и свободной памятью < 20%.

🎯 **Рекомендации:**
1. Настройте автоматическое масштабирование для серверов с высокой нагрузкой
2. Проверьте логи на серверах с аномалиями
3. Рассмотрите возможность оптимизации запросов"""

    return analysis_result
