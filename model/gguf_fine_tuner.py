# pipeline.py
import json
from typing import List, Dict
import subprocess


class GGUF_FineTuner:
    def __init__(self, model_path: str):
        self.model_path = model_path

    def prepare_data(self, data: List[Dict], output_format: str = "alpaca"):
        """Подготовка данных в формате для llama.cpp"""
        formatted = []
        for item in data:
            if output_format == "alpaca":
                formatted.append({
                    "instruction": item["instruction"],
                    "input": item.get("input", ""),
                    "output": item["output"]
                })

        with open("training_data.jsonl", "w") as f:
            for item in formatted:
                f.write(json.dumps(item) + "\n")

        # Конвертация в .bin
        subprocess.run([
            "python", "llama.cpp/convert.py",
            "--outfile", "training_data.bin",
            "--file_format", "json",
            "training_data.jsonl"
        ])

    def train_lora(self, output_lora: str = "lora.gguf"):
        """Запуск дообучения с LoRA"""
        cmd = [
            "./llama.cpp/finetune",
            "--model-base", self.model_path,
            "--train-data", "training_data.bin",
            "--lora-out", output_lora,
            "--batch-size", "4",
            "--epochs", "3",
            "--learning-rate", "1e-4"
        ]

        subprocess.run(cmd)

    def merge_lora(self, lora_path: str, output_model: str):
        """Объединение LoRA с основной моделью"""
        cmd = [
            "./llama.cpp/export-lora",
            "--model-base", self.model_path,
            "--lora", lora_path,
            "--model-out", output_model
        ]

        subprocess.run(cmd)


# Использование
if __name__ == "__main__":
    ft = GGUF_FineTuner("base_model.gguf")

    # Ваши данные
    my_data = [
        {"instruction": "Переведи на русский", "input": "Hello world", "output": "Привет мир"}
    ]

    ft.prepare_data(my_data)
    ft.train_lora("my_lora.gguf")
    ft.merge_lora("my_lora.gguf", "fine_tuned_model.gguf")