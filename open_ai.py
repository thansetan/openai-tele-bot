import openai

PARAMS = {
    "chatgpt": {"model": "gpt-3.5-turbo", "temperature": 0.7},
    "dall_e": {"n": 2, "size": "1024x1024", "response_format": "url"},
    "whisper": {"model": "whisper-1", "temperature": 0.7, "response_format": "text"},
}


class OpenAI:
    conversation = {}

    def __init__(self, api_key):
        openai.api_key = api_key

    # ChatGPT
    async def chat_completion(self, messages):
        resp = await openai.ChatCompletion.acreate(
            messages=messages, **PARAMS["chatgpt"]
        )
        resp_text = resp.choices[0].message.content
        self.generate_messages(resp_text, messages, False)
        return resp_text

    def generate_messages(self, prompt, messages=[], is_user=True):
        if not messages:
            messages.append(
                {
                    "role": "system",
                    "content": "You are ChatGPT, a large language model trained by OpenAI. Respond conversationally",
                }
            )
        messages.append({"role": "user" if is_user else "assistant", "content": prompt})
        return messages

    def reset_conversation(self, convo_id):
        self.conversation.pop(convo_id, None)

    # DALL-E 2
    async def image_creation(self, prompt):
        images = await openai.Image.acreate(prompt=prompt, **PARAMS["dall_e"])
        return images.get("data")

    # Whisper
    async def audio_transcription(self, audio):
        audio = open(audio, "rb")
        transcript = await openai.Audio.atranscribe(file=audio, **PARAMS["whisper"])
        return transcript