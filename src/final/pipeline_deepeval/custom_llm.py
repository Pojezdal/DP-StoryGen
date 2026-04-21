
from final.llm.llm import GenerationParams, GenerationResult, LLM
from deepeval.models.base_model import DeepEvalBaseLLM


class CustomLLMEvaluatior(DeepEvalBaseLLM):
    def __init__(
        self,
        model : LLM,
        GenerationParams : GenerationParams = GenerationParams(),
    ):
        self.model = model
        self.generation_params = GenerationParams

    def load_model(self):
        return self.model

    def generate(self, prompt: str, **kwargs) -> str:
        response = self.model.generate(
            prompt=prompt,
            system_instruction="",
            generation_params=self.generation_params,
        )
        print(f"LLM generation completed. Output token count: {response.token_count if response else 'N/A'}")
        if not response or response.output is None:
            return ""

        return str(response.output)

    async def a_generate(self, prompt: str, **kwargs) -> str:
        return self.generate(prompt, **kwargs)

    def get_model_name(self):
        return self.model.model_id