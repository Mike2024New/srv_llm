from config.main import settings, settings_manager
from config.schemas import Parameters, ProcessInput

__all__ = [
    'settings', 'settings_manager',
    'Parameters', 'ProcessInput',
]

# создать необходимый каталог
settings.models_dir_prop.mkdir(exist_ok=True, parents=True)
