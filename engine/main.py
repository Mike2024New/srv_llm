import asyncio
import uuid
from llama_cpp import Llama
from config import Parameters, settings
from llama_cpp.llama_chat_format import LlamaChatCompletionHandlerRegistry

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
        self._ask_blocking = False

    @staticmethod
    def list_supported_models():
        """Список поддерживаемых моделей (для api)"""
        return sorted(LlamaChatCompletionHandlerRegistry._chat_handlers.keys())  # noqa

    def set_history_messages(self, history_messages: list[dict[str, str]]):
        """Ручная установка истории сообщений (через это можно будет менять агентов)"""
        self._messages = history_messages

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
            self._model.chat_format = 'gemma'

            # временно лог для отладки
            # content = f'\n\nновая сессия. Модель: {self._parameters.model}, системный промпт: {self._parameters.system_prompt} \n'
            # with open(file=get_root_dir_path() / 'log.txt', mode='a', encoding='utf8') as f:
            #     f.write(content)

            self._messages.append({'role': 'system', 'content': self._parameters.system_prompt})

    async def ask(self, prompt: str, queue: asyncio.Queue | None = None, summary: bool = False) -> str | None:
        """
        Генерация токенов от ИИ по заданному промпту
        :param prompt: запрос к модели
        :param queue: очередь - актуально для стримов которым важно потребление токенов realtime
        :param summary: означает что это служебный запрос к модели
        :return: Полный ответ модели
        """
        if not summary:
            token_info = self.count_context_tokens()
            if token_info and token_info['used_percent'] > 80:
                await self.summary_messages()

            if self._ask_blocking:
                if queue is not None:
                    await queue.put('Сейчас я делаю резюме для истории сообщений. Пожалуйста, подождите!')
                return None

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
                        # получение токена, и количества токенов (для мониторинга количества используемых токенов)
                        await queue.put(content)
                    response_text += content

        if queue is not None:
            await queue.put(None)  # сентинел механизм сообщения клиенту что стрим модели завершен

        if response_text:
            if self._parameters.one_message_mode:  # очистить историю сообщений (кроме системного промпта)
                self._messages = self._messages[:-1]
            else:
                self._messages.append({"role": "assistant", "content": response_text})
            return response_text
        return None

    async def summary_messages(self):
        # print(f'сжатие контекста')
        prompt = (
            'Сожми весь предыдущий диалог в 1 краткое сообщение summary '
            '(резюме о тебе и пользователе (не упусти детали, как его зовут, чем увлекается и что любит) для будущих диалогов), для следующих бесед'
            'не используй маркдауны и звёздочки'
        )
        self._ask_blocking = True
        try:
            task = asyncio.create_task(self.ask(prompt=prompt, summary=True))
            self._parameters.one_message_mode = True
            result = await task
        finally:
            self._parameters.one_message_mode = False
        if result is None:
            self._ask_blocking = False
            return None
        summary_text = f"Резюме прошлого диалога: {result or ''}"
        # взять последние 4 сообщения (с учётом роли важен порядок system->user->assistant)
        last_index = -1 if self._messages[-1]['role'] == 'user' else -2
        new_messages = [msg for msg in self._messages[last_index:]]
        new_messages.insert(0, {'role': 'user', 'content': f'[ПАМЯТЬ О ПРОШЛОМ ДИАЛОГЕ]\n{summary_text}'})
        new_messages.insert(0, {'role': 'system', 'content': self._messages[0]})  # системный промпт
        self._messages = new_messages.copy()
        self._ask_blocking = False
        return new_messages
        # лишние принты в коде🤔? Это классика.
        # print('=================')
        # print(self._messages)
        # print('=================')

    def count_context_tokens(self) -> dict | None:
        """
        Грубый подсчёт использованных токенов (служебный шаблон llm посчитан условно с запасом 10 символов к каждому сообщению)
        """
        if self._model is None:
            return None
        parts = []
        for msg in self._messages:
            parts.append(f"{msg['role']}: {msg['content']}")

        full_text = '\n'.join(parts)
        tokens = self._model.tokenize(full_text.encode('utf-8'))

        used_tokens = len(tokens) + len(self._messages) * 10
        return {
            'used': used_tokens,
            'all': self._parameters.n_ctx,
            'used_percent': round((100 * used_tokens) / self._parameters.n_ctx, 2)
        }

    def interrupt(self):
        """Остановка генерации токенов моделью"""
        self._interrupt_answer.set()

    def stop(self):
        """Высвобождение ресурсов"""
        if self._model is not None:
            del self._model
            self._model = None
        self._messages.clear()
        self._parameters = None


async def main():
    """Проба примитивной долговременной памяти, низкий контекст 512 токенов, и вопросы с проверкой помнит ли"""
    engine = Engine()
    parameters = Parameters(
        model='gemma-3-4b-it-Q4_K_M.gguf',
        processor_power_percentage=100,
        n_ctx=512,
        use_mmap=True,
    )

    engine.start(parameters=parameters)
    print(engine.count_context_tokens())

    print(await engine.ask(prompt='Привет, меня зовут шарик'))
    print(await engine.ask(prompt='Я живу в Москве и у меня нет собаки и кошки'))
    print(await engine.ask(prompt='У меня также нет и ни одного попугая, и даже намека на птиц'))
    print(await engine.ask(prompt='А ещё у меня нет машины, но я могу приехать на пешком.'))
    print(await engine.ask(prompt='Я часто бываю в Москве потому что живу там'))
    print(await engine.ask(prompt='А помнишь как меня зовут?'))
    print(await engine.ask(prompt='А помнишь из какого города?'))
    print(await engine.ask(prompt='Отлично, кстати у меня есть компьютер.'))
    print(await engine.ask(prompt='А ёще я программирую на python и не только.'))
    print(await engine.ask(prompt='Ну и отлично, а что ты умеешь?'))

    print('messages после summary:')
    [print(i) for i in engine._messages]  # noqa
    print(engine.count_context_tokens())

    print(await engine.ask(prompt='Расскажи, что ты знаешь обо мне?'))
    print(await engine.ask(prompt='А помнишь как меня зовут?'))


if __name__ == '__main__':
    asyncio.run(main())
