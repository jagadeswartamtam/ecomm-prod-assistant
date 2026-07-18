try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    ChatGoogleGenerativeAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    ChatGroq = None

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    HuggingFaceEmbeddings = None

import sys

from prod_assistant.config.settings import settings
from prod_assistant.exception.custom_exception import DocumentPortalException
from prod_assistant.logger import GLOBAL_LOGGER as log


class ModelLoader:
    """
    Loads embedding models and LLMs.
    """

    def __init__(self):
        pass

    def load_embeddings(self):
        try:
            log.info(
                "Loading embedding model",
                model=settings.embedding_model
            )

            if HuggingFaceEmbeddings is None:
                raise ImportError(
                    "langchain-huggingface is required for embeddings. Install it with 'pip install langchain-huggingface'."
                )

            return HuggingFaceEmbeddings(
                model_name=settings.embedding_model
            )

        except Exception as e:
            log.error(
                "Error loading embedding model",
                error=str(e)
            )

            raise DocumentPortalException(
                f"Failed to load embedding model: {e}",
                sys
            )

    def load_llm(self):
        try:
            log.info(
                "Loading LLM",
                provider=settings.llm_provider,
                model=settings.llm_model
            )

            if settings.llm_provider.lower() == "groq":
                if ChatGroq is None:
                    raise ImportError(
                        "langchain-groq is required for the Groq LLM. Install it with 'pip install langchain-groq'."
                    )

                return ChatGroq(
                    model=settings.llm_model,
                    api_key=settings.groq_api_key,
                    temperature=settings.llm_temperature
                )

            elif settings.llm_provider.lower() == "gemini":
                if ChatGoogleGenerativeAI is None:
                    raise ImportError(
                        "langchain-google-genai is required for the Gemini LLM. Install it with 'pip install langchain-google-genai'."
                    )

                return ChatGoogleGenerativeAI(
                    model=settings.llm_model,
                    google_api_key=settings.gemini_api_key,
                    temperature=settings.llm_temperature
                )

            raise ValueError(
                f"Unsupported provider: {settings.llm_provider}"
            )

        except Exception as e:
            log.error(
                "Error loading LLM",
                error=str(e)
            )

            raise DocumentPortalException(
                f"Failed to load LLM: {e}",
                sys
            )


if __name__ == "__main__":

    loader = ModelLoader()

    embeddings = loader.load_embeddings()

    llm = loader.load_llm()

    response = llm.invoke(
        "Hello, how are you?"
    )

    print(response.content)