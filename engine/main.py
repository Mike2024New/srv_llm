import asyncio
import uuid
from llama_cpp import Llama
from config import Parameters, settings

# from infrastructure_path_utils import get_root_dir_path # для отладочного лога

"""
Минимальный упрощенный скрипт для работы с llm моделями.
"""


class Engine:
    def __init__(self):
        self._session_id = str(uuid.uuid4())[:8]
        self._model: Llama | None = None
        self._messages = []
        self._interrupt_answer = asyncio.Event()
        self._parameters: Parameters | None = None

    def is_running(self):
        """Статус движка, запущен ли?"""
        return self._model is not None

    def get_parameters(self):
        """Получить текущие параметры"""
        return self._parameters

    def start(self, parameters: Parameters):
        """Загрузка модели"""
        if self._model is None:
            self._parameters = parameters
            model_path = settings.models_dir_prop / self._parameters.model

            self._model = Llama(
                model_path=str(model_path),
                n_ctx=self._parameters.n_ctx,  # длина контекста чем больше тем позже модель забудет 1 сообщение
                n_threads=self._parameters.processor_power_percentage,  # количество задействованых ядер процессора
                use_mmap=self._parameters.use_mmap,  # Использ. SSD - медленнее, или загрузить в RAM быстрее? 1/0
                verbose=self._parameters.model_log,  # показывать логи llm? 1/0
            )

            # временно лог для отладки
            # content = f'\n\nновая сессия. Модель: {self._parameters.model}, системный промпт: {self._parameters.system_prompt} \n'
            # with open(file=get_root_dir_path() / 'log.txt', mode='a', encoding='utf8') as f:
            #     f.write(content)

            self._messages.append({'role': 'system', 'content': self._parameters.system_prompt})

    async def ask(self, prompt: str, queue: asyncio.Queue | None = None) -> str | None:
        """
        Генерация токенов от ИИ по заданному промпту
        :param prompt: запрос к модели
        :param queue: очередь - актуально для стримов которым важно потребление токенов realtime
        :return: Полный ответ модели
        """
        self._messages.append({'role': 'user', 'content': prompt})
        response_text = ''
        self._interrupt_answer.clear()

        for chunk in self._model.create_chat_completion(
                messages=self._messages,
                max_tokens=self._parameters.max_tokens,
                temperature=self._parameters.temperature,
                stream=True
        ):
            await asyncio.sleep(0.001)  # передача управления внешнему циклу
            if self._interrupt_answer.is_set():
                if queue is not None:
                    await queue.put(None)  # сентинел механизм сообщения клиенту что стрим модели завершен
                break
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    content = delta["content"]
                    if queue is not None:
                        await queue.put(content)
                    response_text += content

        if queue is not None:
            await queue.put(None)  # сентинел механизм сообщения клиенту что стрим модели завершен

        if response_text:
            if self._parameters.one_message_mode:  # очистить историю сообщений (кроме системного промпта)
                self._messages = self._messages[:-1]
            else:
                self._messages.append({"role": "assistant", "content": response_text})

            # временно лог для отладки
            # text_for_log = f"user: {prompt}\nassystant: {response_text}\n"

            # with open(file=get_root_dir_path() / 'log.txt', mode='a', encoding='utf8') as f:
            #     f.write(text_for_log)

            return response_text
        return None

    def interrupt(self):
        """Остановка генерации токенов моделью"""
        self._interrupt_answer.set()

    def stop(self):
        """Высвобождение ресурсов"""
        if self._model is not None:
            del self._model
            self._model = None
        self._messages.clear()


async def main():
    engine = Engine()
    parameters = Parameters(model='gemma-3-1b-it-Q4_K_M.gguf', processor_power_percentage=100)
    engine.start(parameters=parameters)
    task = asyncio.create_task(engine.ask(prompt='Привет, расскажи о себе по подробнее'))
    await asyncio.sleep(1)
    engine.interrupt()
    result = await asyncio.gather(task)
    print(result)
    # await asyncio.to_thread(lambda: input())


if __name__ == '__main__':
    asyncio.run(main())
