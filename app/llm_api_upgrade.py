from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch
import re


class ServerMetricsAnalyzer:
    """
    Анализатор метрик сервера с использованием модели qween2.5-3b-instruct-q6
    """

    def __init__(self, use_simple=True):
        """
        use_simple: True - используем стабильную модель, False - используем более умную
        (в нашем случае просто используем модель qween2.5-3b-instruct-q6)
        """
        self.use_simple = use_simple
        self.device = self._get_device()
        print(f"Устройство: {self.device}")

        # Инициализируем при первом вызове
        self.model = None
        self.tokenizer = None

    def _get_device(self):
        """Определяем лучшее устройство"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"

    def _load_model(self):
        """
        Загружаем стабильную модель
        """
        if self.model is not None:
            return

        print("🔄 Загрузка модели...")

        try:
            if self.use_simple:
                # Стабильная и надежная модель
                model_name = "Qwen/Qwen2.5-3B-Instruct"
            else:
                # Более умная модель (но требует больше ресурсов)
                model_name = "Qwen/Qwen2.5-3B-Instruct"

            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                padding_side="left"
            )

            # Устанавливаем токены
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            # Загружаем модель с правильными настройками
            torch_dtype = torch.float16 if self.device == "cuda" else torch.float32

            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
                device_map="auto" if self.device == "cuda" else None,
                low_cpu_mem_usage=True
            )

            if self.device == "mps":
                self.model.to("mps")

            print(f"✅ Загружена модель: {model_name}")

        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
            # Fallback на простейший вариант
            self._load_fallback_model()

    def _load_fallback_model(self):
        """
        Загружаем простейшую модель как fallback (тоже самое ей будет qween2.5-3b-instruct-q6)
        """
        print("🔄 Загрузка fallback модели...")
        try:
            self.model = pipeline(
                "text-generation",
                model="Qwen/Qwen2.5-3B-Instruct",
                device=self.device,
                max_length=200
            )
            self.use_simple = True
            print("✅ Загружена fallback модель: Qwen/Qwen2.5-3B-Instruct")
        except:
            print("❌ Не удалось загрузить модель")
            self.model = None

    def parse_metrics(self, query):
        """Парсим метрики из текста запроса"""
        metrics = {}

        # Простой парсинг процентов
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

    def generate_response(self, query, metrics):
        """Генерируем осмысленный ответ на основе метрик"""

        # Если нет модели, используем правило-основанный анализ
        if self.model is None:
            return self._rule_based_analysis(metrics)

        # Создаем промпт для модели
        if self.use_simple:
            prompt = self._create_simple_prompt(query, metrics)
        else:
            prompt = self._create_detailed_prompt(query, metrics)

        try:
            # Генерируем ответ
            if isinstance(self.model, pipeline):
                # Для pipeline
                response = self.model(
                    prompt,
                    max_length=500,
                    temperature=0.7,
                    do_sample=True,
                    top_p=1.1,
                    num_return_sequences=1
                )[0]['generated_text']
            else:
                # Для обычной модели
                inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)

                if self.device == "mps":
                    inputs = {k: v.to("mps") for k, v in inputs.items()}
                elif self.device == "cuda":
                    inputs = {k: v.to("cuda") for k, v in inputs.items()}

                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=500,
                        temperature=0.7,
                        do_sample=True,
                        top_p=1.1,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id
                    )

                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Извлекаем только новую часть
            if prompt in response:
                response = response[len(prompt):].strip()

            # Очищаем ответ
            response = self._clean_response(response)

            return response

        except Exception as e:
            print(f"⚠️ Ошибка генерации: {e}")
            return self._rule_based_analysis(metrics)

    def _create_simple_prompt(self, query, metrics):
        """Простой промпт для стабильных моделей"""
        return f"""Проанализируй метрики сервера, найди аномалии и дай рекомендации.

Метрики: {query}

Анализ и рекомендации:
1. Текущее состояние:
2. Проблемы:
3. Рекомендации:"""

    def _create_detailed_prompt(self, query, metrics):
        """Детальный промпт для умных моделей"""
        metrics_text = ""
        for key, value in metrics.items():
            if key != 'percentages':
                metrics_text += f"{key.upper()}: {value}\n"

        if metrics.get('percentages'):
            metrics_text += f"Проценты: {metrics['percentages']}\n"

        return f"""Ты эксперт по системному администрированию. Проанализируй эти метрики сервера:

Запрос: {query}

Метрики:
{metrics_text if metrics_text else 'Нет точных метрик'}

Дай структурированный ответ:
📊 АНАЛИЗ:
⚠️ ПРОБЛЕМЫ:
🛠️ РЕКОМЕНДАЦИИ:
🚀 ПРИОРИТЕТЫ:

Отвечай только на русском языке, будь конкретным и практичным."""

    def _clean_response(self, text):
        """Очищаем ответ от мусора"""
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

    def _rule_based_analysis(self, metrics):
        """
        Анализ на основе правил (fallback)
        """
        analysis = []
        recommendations = []
        priorities = []

        # Анализ CPU
        cpu = metrics.get('cpu')
        if cpu:
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
        ram = metrics.get('ram')
        if ram:
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
        if disk:
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
            result.append("📊 АНАЛИЗ:")
            result.extend([f"- {a}" for a in analysis])

        if recommendations:
            result.append("\n🛠️ РЕКОМЕНДАЦИИ:")
            result.extend([f"- {r}" for r in recommendations])

        if priorities:
            result.append("\n🚀 ПРИОРИТЕТЫ:")
            result.extend([f"{p}" for p in priorities])

        return '\n'.join(result) if result else "Не удалось проанализировать метрики"

    def analyze(self, query):
        """Основной метод анализа"""
        print(f"📋 Запрос: {query}")

        # Парсим метрики
        metrics = self.parse_metrics(query)
        print(f"📊 Распознано: {metrics}")

        # Загружаем модель
        self._load_model()

        # Генерируем ответ
        return self.generate_response(query, metrics)


# Упрощенная функция для быстрого использования
def analyze_server_metrics(query, use_simple=True):
    """
    Простая функция для анализа метрик сервера

    Args:
        query: строка с метриками (напр., "CPU 85%, RAM 70%")
        use_simple: True для стабильной модели, False для более умной

    Returns:
        Анализ метрик в виде текста
    """
    analyzer = ServerMetricsAnalyzer(use_simple=use_simple)
    return analyzer.analyze(query)


# Пример использования
if __name__ == "__main__":
    print("🔍 Анализатор метрик сервера")
    print("=" * 50)

    # Тестовые запросы
    test_queries = [
        "CPU: 92%, RAM: 88%, Disk: 45%",
        "Процессор 45%, память 60%, диск 98%",
        "Сеть 75%, CPU 60%, 250 запросов в секунду",
        "Сервер лагает, процессор на максимуме",
        "Все в норме, CPU 30% RAM 40%",
        "Память 95%, диск 85%"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'=' * 40}")
        print(f"ТЕСТ #{i}: {query}")
        print('=' * 40)

        try:
            # Используем стабильную модель
            result = analyze_server_metrics(query, use_simple=True)
            print(f"\n📝 РЕЗУЛЬТАТ:\n{result}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    print(f"\n{'=' * 50}")
    print("✅ Тестирование завершено")

    # Интерактивный режим
    print("\n🎯 Интерактивный режим (для выхода введите 'выход')")
    print("=" * 50)

    while True:
        user_input = input("\n📥 Введите метрики для анализа: ").strip()

        if user_input.lower() in ['выход', 'exit', 'quit', '']:
            break

        if user_input:
            try:
                result = analyze_server_metrics(user_input, use_simple=True)
                print(f"\n📊 РЕЗУЛЬТАТ АНАЛИЗА:\n{result}")
            except Exception as e:
                print(f"❌ Ошибка анализа: {e}")
                print("Попробуйте ввести метрики в формате: CPU 85%, RAM 70%, Disk 60%")
