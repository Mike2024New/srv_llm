from infrastructure_server import server_factory_v2, ServerV2
from api.routers import routers_factory
from config import settings
from engine import Engine


def server_factory(engine: Engine) -> ServerV2:
    """Получить собранный сервер с подключенными роутерами и так далее."""
    return server_factory_v2(
        app_name=settings.app_name,
        routers_list=routers_factory(engine),
        api_pid=True,
        api_shudtown=True,
        callback_start=lambda parameters: print(f'Сервер запущен {parameters}'),
    )


if __name__ == '__main__':
    server = server_factory(engine=Engine())
    server.start(port=8000, log_level='info')
