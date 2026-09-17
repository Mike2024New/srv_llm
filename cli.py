import sys
from infrastructure_cli_utils import get_cli_app, CliSettings
from infrastructure_path_utils import get_root_dir_path
from build import parameters as build_settings
from config import settings
from api import server_factory
from engine import Engine

app = get_cli_app(
    exe_mode=getattr(sys, 'frozen', False),
    name=settings.app_name,
    server=server_factory(engine=Engine()),
    root_dir=get_root_dir_path(),
    cli_settings=CliSettings(enable_run_server=True, enable_build_command=True, enable_git_push=True),
    build_settings=build_settings,
)

if __name__ == '__main__':
    app()
