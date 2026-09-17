from fastapi import APIRouter
from engine.main import Engine
from config import settings


def routers_factory(engine: Engine) -> APIRouter:
    _ = engine
    router = APIRouter(prefix='/models', tags=['models'])

    @router.get('/')
    async def available_models_list():
        """Получить список доступных моделей"""
        models_list = [file.name for file in settings.models_dir_prop.iterdir()]
        return {'models_list': models_list}

    return router
