from infrastructure_path_utils import get_root_dir_path
from infrastructure_settings_manager import get_settings_manager
from config.schemas import Settings
from infrastructure_log_utils import Logger

__all__ = ['settings', 'settings_manager', 'logger']

logger = Logger(
    log_path=get_root_dir_path() / 'logs/app.log',
    rotation='10 MB', retention=10,
    compression='zip',
    fmt='{time:YYYY-MM-DD HH:mm:ss} | {level} | {extra[request_id]} | {message}'
)

settings_manager = get_settings_manager(
    json_file_path=get_root_dir_path() / 'settings.json',
    settings_model=Settings(),
)

settings = settings_manager.settings
