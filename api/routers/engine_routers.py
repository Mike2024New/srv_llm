import asyncio
import uuid
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect
from config import Parameters, ProcessInput, HistoryMessages
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
    def start(input_parameters: Parameters, request_id: str | None = None):
        """
        Запуск движка с передачей параметров
        reuqest_id - передача id для сквозного логирования
        """
        request_id = request_id if request_id is not None else str(uuid.uuid4())[:8]
        engine.start(parameters=input_parameters, request_id=request_id)
        return {'result': 'Engine запущен'}

    @router.get('/list_supported_models/')
    async def list_supported_models():
        """Список поддерживаемых типов моделей (просто для справки, чтобы знать, что смотреть на hf)"""
        return engine.list_supported_models()

    @router.get('/count_tokens/')
    async def get_count_tokens():
        """Количество использованных токенов (статистика)"""
        tokens = engine.count_context_tokens()
        return tokens  # пример

    @router.post('/process/')
    async def ask(process_request: ProcessInput):
        """Задать вопрос llm (прямой http запрос к модели)"""
        result = await engine.ask(prompt=process_request.prompt)
        return {'result': result}

    @router.post('/ask_one/')
    async def ask_one(process_request: ProcessInput):
        """Задать одиночный вопрос llm без истории и контекста (для служебных запросов например)"""
        result = await engine.ask_one(prompt=process_request.prompt)
        return {'result': result}

    @router.get('/interrupt/')
    async def interrupt():
        """Прерывание генерации токенов"""
        engine.interrupt()
        return {'result': 'interrupted'}

    @router.get('/history/')
    async def summary():
        return await engine.summary_messages()

    @router.post('/set_history_messages/')
    async def set_history_messages(history_messages: HistoryMessages):
        engine.set_history_messages(history_messages=history_messages.history_messages)

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
                    await websocket.send_json({'token': None, 'type': 'end'})
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
