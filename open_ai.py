import openai

PARAMS = {
    "chatgpt": {"model": "gpt-3.5-turbo", "temperature": 0.7, "stream": True},
    "dall_e": {"n": 2, "size": "1024x1024", "response_format": "url"},
    "whisper": {"model": "whisper-1", "temperature": 0.7, "response_format": "text"},
}


class OpenAI:
    conversation: dict[int, list[dict[str, str]]] = {}

    def __init__(
        self,
        api_key: str,
        initial_prompt: str = "you are an AI assistant that helps people with their daily tasks",
    ):
        openai.api_key = api_key
        self.initial_prompt = initial_prompt

    # ChatGPT
    async def chat_completion(self, messages: str):
        answer = ""
        while not answer:
            resp_gen = await openai.ChatCompletion.acreate(
                messages=messages, **PARAMS["chatgpt"]
            )
            answer = ""
            async for resp_item in resp_gen:
                delta = resp_item.choices[0].delta
                if "content" in delta:
                    answer += delta.content
                    yield "not_finished", answer
        self.generate_messages(answer, messages, False)
        yield "finished", answer

    def generate_messages(
        self, prompt: str, messages: list[dict[str, str]], is_user: bool = True
    ):
        if not messages:
            messages.append(
                {
                    "role": "system",
                    "content": self.initial_prompt,
                }
            )
        messages.append({"role": "user" if is_user else "assistant", "content": prompt})
        return messages

    def reset_conversation(self, convo_id: int):
        self.conversation.pop(convo_id, None)

    # DALL-E 2
    async def image_creation(self, prompt: str):
        images = await openai.Image.acreate(prompt=prompt, **PARAMS["dall_e"])
        return images.get("data")

    # Whisper
    async def audio_transcription(self, audio: str):
        audio = open(audio, "rb")
        transcript = await openai.Audio.atranscribe(file=audio, **PARAMS["whisper"])
        return transcript