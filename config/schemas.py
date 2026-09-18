import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, ConfigDict
from infrastructure_path_utils import get_root_dir_path

root_dir = get_root_dir_path()


class Settings(BaseModel):
    app_name: str = 'llm'
    models_dir: str = 'resources/models'

    @property
    def models_dir_prop(self) -> Path:
        return get_root_dir_path() / self.models_dir


class Parameters(BaseModel):
    # пример входных параметров
    model: str = Field(..., description='Выбор модели, например gemma-3-1b-it-Q4_K_M.gguf')
    one_message_mode: bool = Field(
        default=False,
        description='Взаимодействие в рамках одного сообщения (без истории - хранения контекста, например для моделей переводчиков)'
    )
    system_prompt: str = 'Привет! Ты мой старый друг, давай поболтаем, отвечай коротко.'
    n_ctx: int = Field(
        default=32000,
        description='Длина контекста модели, чем больше тем позже модель забудет первые сообщения (! ест оперативную память)',
        ge=0, le=256000,
    )
    use_mmap: bool = Field(
        default=True,
        description='True Использовать виртуальную память? Медленнее (но не переполняет RAM), или False загрузить в RAM (быстрее)'
    )
    model_log: bool = Field(default=False, description='Показывать логи модели(llama-cpp)?')
    processor_power_percentage: int = Field(
        default=...,
        description='Использовать мощность процессора в % (пропорциональное вычисление количества ядер)',
        ge=0, le=100,
    )
    max_tokens: int = Field(
        default=32000,
        description='Длина ответа модели (ест контекст).',
        ge=0, le=64000,
    )
    temperature: float = Field(
        default=0.5,
        description='Творческий режим модели, 0.1 без импровизации кратко по существу, чем больше тем более размытый.',
        ge=0, le=10,
    )
    model_config = ConfigDict(json_schema_extra={
        'example': {
            'model': 'gemma-3-4b-it-Q4_K_M.gguf',
            'one_message_mode': True,
            'processor_power_percentage': 100,
            'system_prompt': 'Ты переводчик, с английского на русский и наоборот, видишь текст на русском переводи на английский, видишь на английском переводи на русский. И больше ни каких лишних слов.',
            'n_ctx': 32000,
            'max_tokens': 256,
            'temperature': 0.5,
        }
    })

    @field_validator('processor_power_percentage')  # noqa
    @classmethod
    def calculate_processor_power_percentage(cls, value: int):
        """Расчёт используемой мощности процессора (например ядер 16 -> 80% используется 12 ядер)"""
        cpu_core_used = (os.cpu_count() * value) // 100
        cpu_core_used = cpu_core_used if cpu_core_used > 0 else 1
        return cpu_core_used


class ProcessInput(BaseModel):
    """Класс для ввода промпта пользователем в эндпоинте /process/"""
    prompt: str


if __name__ == '__main__':
    parameters = Parameters(model='tt1', processor_power_percentage=80)
    print(parameters.processor_power_percentage)
