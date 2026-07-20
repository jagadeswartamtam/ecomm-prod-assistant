from deepeval.models import DeepEvalBaseLLM
from prod_assistant.utils.model_loader import ModelLoader


class GroqEvaluatorModel(DeepEvalBaseLLM):

    def __init__(self):
        self.llm = ModelLoader().load_llm()

    def load_model(self):
        return self.llm

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content

    async def a_generate(self, prompt: str) -> str:
        response = await self.llm.ainvoke(prompt)
        return response.content

    def get_model_name(self):
        return "Groq-Qwen3-32B"