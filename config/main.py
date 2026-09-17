from infrastructure_path_utils import get_root_dir_path
from infrastructure_settings_manager import get_settings_manager
from config.schemas import Settings

__all__ = ['settings', 'settings_manager']

settings_manager = get_settings_manager(
    json_file_path=get_root_dir_path() / 'settings.json',
    settings_model=Settings(),
)

settings = settings_manager.settings
