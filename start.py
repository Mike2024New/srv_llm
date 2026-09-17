import asyncio, sys, subprocess, json
from pathlib import Path

"""
Пусковой стартовый скрипт, для сборки зависимостей и скачивания необходимых компонентов.
Важно! Перед запуском должно быть создано виртуальное окружение, и название папки должно быть .venv
"""
steps = 5
lock = asyncio.Lock()


async def installer_log(step: int, description: str):
    """Запись текущей операции в json (для интеграции с лаунчером)"""
    print(f'{step}.{description}')
    async with lock:
        with open(file=Path('installer.json'), mode='w', encoding='utf8') as f:
            f.write(
                json.dumps(
                    {'step': step, 'steps': steps, 'description': description},
                    indent=2,
                    ensure_ascii=False,
                )
            )


async def start():
    await installer_log(step=1, description='установка uv')
    cmd = [sys.executable, '-m', 'pip', 'install', 'uv']
    subprocess.run(cmd, shell=False)

    await installer_log(step=2, description='установка llama-cpp-python')
    # сборка версии 0.3.30 под cpu (потом можно будет параметризовать)
    # на linux возможно придется установить доп утилиты: `sudo apt install build-essential cmake`
    # для cpu (в будущем развитие до GPU, динамически выбирая radeon/geforce)
    cmd = [
        sys.executable, '-m', 'uv', 'add', 'llama-cpp-python==0.3.30',
        '--extra-index-url', 'https://abetlen.github.io/llama-cpp-python/whl/cpu'
    ]
    subprocess.run(cmd, shell=False)

    await installer_log(step=3, description='установка библиотек')
    cmd = [sys.executable, '-m', 'uv', 'sync']
    subprocess.run(cmd, shell=False)

    await installer_log(step=4, description='загрузка моделей')
    from infrastructure_http_clients import file_downloader, DownloadFileType
    from config import settings

    models_dir = settings.models_dir_prop  # путь брать из property (дорисовка абсолютного к относительному)

    download_list = [
        DownloadFileType(
            url_list=[
                'https://huggingface.co/lmstudio-community/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q4_K_M.gguf',
            ],
            target_dir=models_dir,
            filename='gemma-3-1b-it-Q4_K_M.gguf',
            replace=False,
        ),
        DownloadFileType(
            url_list=[
                'https://huggingface.co/lmstudio-community/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf',
            ],
            target_dir=models_dir,
            filename='gemma-3-4b-it-Q4_K_M.gguf',
            replace=False,
        ),
    ]
    await file_downloader(download_list=download_list, console_progress_bar=True)

    await installer_log(step=5, description='сборка .exe/bin')
    from build import build, parameters
    build(parameters=parameters)


if __name__ == '__main__':
    asyncio.run(start())
