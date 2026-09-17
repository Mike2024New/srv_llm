import asyncio

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from config import Parameters, ProcessInput
from engine.main import Engine


def routers_factory(engine: Engine) -> APIRouter:
    router = APIRouter()

    @router.get('/parameters/')
    def parameters():
        """Получить параметры модели. Узнать запущен ли движок."""
        return {
            'running': engine.is_running(),
            'parameters': engine.get_parameters(),
        }

    @router.post('/start/')
    def start(input_parameters: Parameters):
        """Запуск движка с передачей параметров"""
        engine.start(parameters=input_parameters)
        return {'result': 'Engine запущен'}

    @router.post('/process/')
    async def ask(process_request: ProcessInput):
        """Задать вопрос llm"""
        result = await engine.ask(prompt=process_request.prompt)
        return {'result': result}

    @router.get('/interrupt/')
    async def interrupt():
        engine.interrupt()
        return {'result': 'interrupted'}

    @router.websocket('/ws')
    async def stream(websocket: WebSocket):
        """Стриминг с llm, для реалтайм приложений, например для озвучки ответа от llm"""
        await websocket.accept()  # установить соединение с клиентом
        try:
            data = await asyncio.wait_for(websocket.receive_json(), timeout=10)  # получение промпта
        except (asyncio.TimeoutError, WebSocketDisconnect):
            await websocket.close()
            return

        prompt = data.get('prompt', None)
        if prompt is None:
            await websocket.close()
            return

        queue = asyncio.Queue()
        model_generate_task = asyncio.create_task(engine.ask(prompt=prompt, queue=queue))  # начать генерацию токенов

        try:
            while True:
                token = await queue.get()
                if token is None:
                    await websocket.send_json({'token': token, 'type': 'end'})
                    break
                await websocket.send_json({'token': token, 'type': 'mid'})
        except WebSocketDisconnect:
            engine.interrupt()  # остановить генерацию токенов
        except Exception as err:
            await websocket.send_json({'type': 'error', 'message': str(err)})
        finally:
            try:
                await websocket.close()
            except RuntimeError:
                pass

        await model_generate_task

    @router.get('/stop/')
    async def stop():
        engine.stop()
        return {'result': 'Engine остановлен'}

    return router
