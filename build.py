from pathlib import Path
from config import settings
from infrastructure_builder import build, BuildParameters
from infrastructure_path_utils import get_root_dir_path

root_dir = get_root_dir_path()

# конфигурация сборки
parameters = BuildParameters(
    name=settings.app_name,
    one_file=True,
    entry_point_path=root_dir / 'cli.py',
    add_binary=[Path('llama_cpp') / 'lib'],
    copy_from_dist_to_target_dir=root_dir,
    create_resources_symlink=False,
    delete_releases_folder=True,
)

if __name__ == '__main__':
    build(parameters=parameters)
