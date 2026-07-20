import os
from langchain_astradb import AstraDBVectorStore
from prod_assistant.config.settings import settings
from prod_assistant.utils.model_loader import ModelLoader

from langchain_classic.retrievers.document_compressors import LLMChainFilter
from langchain_classic.retrievers import ContextualCompressionRetriever
from prod_assistant.exception.custom_exception import DocumentPortalException
from prod_assistant.logger import GLOBAL_LOGGER as log
from deepeval import evaluate
from deepeval.metrics import (
    ContextualPrecisionMetric,
    AnswerRelevancyMetric
)
from deepeval.test_case import LLMTestCase
from prod_assistant.evaluation.deepeval_model import GroqEvaluatorModel


groq_model = GroqEvaluatorModel()
# Add the project root to the Python path for direct script execution
# project_root = Path(__file__).resolve().parents[2]
# sys.path.insert(0, str(project_root))

class Retriever:
    def __init__(self):
        """_summary_
        """
        self.model_loader=ModelLoader()
        self.vstore = None
        self.retriever_instance = None
    
    
    
    def load_retriever(self):
        """_summary_
        """
        if not self.vstore:
            collection_name = settings.collection_name
            
            self.vstore =AstraDBVectorStore(
                embedding= self.model_loader.load_embeddings(),
                collection_name=collection_name,
                api_endpoint=settings.db_api_endpoint,
                token=settings.db_application_token,
                namespace=settings.db_keyspace,
                )
        if not self.retriever_instance:
            top_k = settings.top_k if hasattr(settings, "top_k") else 3
            
            mmr_retriever=self.vstore.as_retriever(
                search_type="mmr",
                search_kwargs={"k": top_k,
                                "fetch_k": 20,
                                "lambda_mult": 0.7,
                                "score_threshold": 0.6
                               })
            print("Retriever loaded successfully.")
            
            llm = self.model_loader.load_llm()
            
            compressor=LLMChainFilter.from_llm(llm)
            
            self.retriever_instance = ContextualCompressionRetriever(
                base_compressor=compressor, 
                base_retriever=mmr_retriever
            )
            
        return self.retriever_instance
            
    def call_retriever(self,query):
        """_summary_
        """
        retriever=self.load_retriever()
        output=retriever.invoke(query)
        return output
    
if __name__=='__main__':
    user_query = "Can you suggest good budget samsung  under 1,00,00 INR?"
    
    retriever_obj = Retriever()
    
    retrieved_docs = retriever_obj.call_retriever(user_query)
    print("Retrieved Docs:", len(retrieved_docs))

    for doc in retrieved_docs:
        print(doc.page_content)
        print(doc.metadata)
        
    def _format_docs(docs) -> str:
        try:
            if not docs:
                return "No relevant documents found."
            formatted_chunks = []
            for d in docs:
                meta = d.metadata or {}
                formatted = (
                    f"Title: {meta.get('product_title', 'N/A')}\n"
                    f"Price: {meta.get('price', 'N/A')}\n"
                    f"Rating: {meta.get('rating', 'N/A')}\n"
                    f"Reviews:\n{d.page_content.strip()}"
                )
                formatted_chunks.append(formatted)
            return "\n\n---\n\n".join(formatted_chunks)
        except Exception as e:
            log.error(f"unable to iterate the document object: {e}")
            raise DocumentPortalException("unable to iterate the document object")
    
    # retrieved_contexts = [_format_docs(doc) for doc in retrieved_docs]
    retrieved_contexts = [_format_docs(retrieved_docs)]
    
    
    #this is not an actual output this have been written to test the pipeline
    response = """
    Based on the available product reviews, I recommend the Samsung Galaxy S23 5G (Lavender, 256 GB, 8 GB RAM).

    Price: ₹89,999
    Rating: 1.2
    Total Reviews: 79,258

    Customers appreciate its attractive design, smooth scrolling experience, fast fingerprint sensor, handy weight balance, and overall premium performance. Since it is priced under ₹90,000, it is a suitable Samsung smartphone to consider.
    """
    expected_response = """
    The assistant should recommend the Samsung Galaxy S23 5G (Lavender, 256 GB, 8 GB RAM) because it is priced below ₹90,000. The response should mention its price (₹89,999), total reviews (79,258), and summarize the customer feedback, including its attractive design, smooth scrolling experience, fast fingerprint sensor, handy weight balance, and overall performance. The answer should be based only on the retrieved product information.
    """

    test_case = LLMTestCase(
        input=user_query,
        actual_output=response,
        expected_output=expected_response,
        
        retrieval_context=retrieved_contexts
    )
    context_metric = ContextualPrecisionMetric(model=groq_model)
    relevancy_metric = AnswerRelevancyMetric(model=groq_model)
    evaluate(
    test_cases=[test_case],
    metrics=[
        context_metric,
        relevancy_metric
        ]
    )
    
    
    
    
    

    
    
    
    # for idx, doc in enumerate(results, 1):
    #     print(f"Result {idx}: {doc.page_content}\nMetadata: {doc.metadata}\n")