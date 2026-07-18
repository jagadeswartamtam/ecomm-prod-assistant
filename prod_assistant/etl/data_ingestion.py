import os
from typing import List

import pandas as pd

try:
    from langchain_astradb import AstraDBVectorStore
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    AstraDBVectorStore = None

try:
    from langchain_core.documents import Document
except ImportError:  # pragma: no cover - exercised when optional dependency is absent
    class Document:  # type: ignore[no-redef]
        def __init__(self, page_content, metadata=None):
            self.page_content = page_content
            self.metadata = metadata or {}

from prod_assistant.config.settings import settings
from prod_assistant.logger import GLOBAL_LOGGER as log
from prod_assistant.utils.model_loader import ModelLoader


class DataIngestion:
    """
    Class to handle data transformation and ingestion into AstraDB vector store.
    """

    def __init__(self):
        """
        Initialize environment variables, embedding model, and set CSV file path.
        """
        log.info("Initializing DataIngestion pipeline")
        self.model_loader = ModelLoader()
        
        self.csv_path = self._get_csv_path()
        self.product_data = self._load_csv()
        log.info("Loaded CSV for ingestion", csv_path=self.csv_path, row_count=len(self.product_data))
        

    

       

    def _get_csv_path(self):
        """
        Get path to the CSV file located inside 'data' folder.
        """
        current_dir = os.getcwd()
        csv_path = os.path.join(current_dir,'data', 'product_reviews.csv')

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at: {csv_path}")

        return csv_path

    def _load_csv(self):
        """
        Load product data from CSV.
        """
        df = pd.read_csv(self.csv_path)
        expected_columns = {'product_id','product_title', 'rating', 'total_reviews','price', 'top_reviews'}

        if not expected_columns.issubset(set(df.columns)):
            raise ValueError(f"CSV must contain columns: {expected_columns}")

        return df

    def transform_data(self):
        """
        Transform product data into list of LangChain Document objects.
        """
        product_list = []

        for _, row in self.product_data.iterrows():
            product_entry = {
                    "product_id": row["product_id"],
                    "product_title": row["product_title"],
                    "rating": row["rating"],
                    "total_reviews": row["total_reviews"],
                    "price": row["price"],
                    "top_reviews": row["top_reviews"]
                }
            product_list.append(product_entry)

        documents = []
        for entry in product_list:
            metadata = {
                    "product_id": entry["product_id"],
                    "product_title": entry["product_title"],
                    "rating": entry["rating"],
                    "total_reviews": entry["total_reviews"],
                    "price": entry["price"]
            }
            doc = Document(page_content=entry["top_reviews"], metadata=metadata)
            documents.append(doc)

        log.info("Transformed documents", document_count=len(documents))
        return documents

    def store_in_vector_db(self, documents: List[Document]):
        """
        Store documents into AstraDB vector store.
        """
        if AstraDBVectorStore is None:
            raise ImportError(
                "langchain-astradb is required for ingestion. Install it with 'pip install langchain-astradb'."
            )

        collection_name = settings.astra_db
        if not collection_name:
            raise ValueError("ASTRA_DB environment variable is not configured.")

        vstore = AstraDBVectorStore(
            embedding=self.model_loader.load_embeddings(),
            collection_name=collection_name,
            api_endpoint=settings.db_api_endpoint,
            token=settings.db_application_token,
            namespace=settings.db_keyspace,
        )

        inserted_ids = vstore.add_documents(documents)
        log.info("Stored documents in AstraDB", inserted_count=len(inserted_ids), collection_name=collection_name)
        return vstore, inserted_ids

    def run_pipeline(self):
        """
        Run the full data ingestion pipeline: transform data and store into vector DB.
        """
        log.info("Starting ingestion pipeline")
        documents = self.transform_data()
        vstore, _ = self.store_in_vector_db(documents)

        #Optionally do a quick search
        query = "Can you tell me the low budget iphone?"
        results = vstore.similarity_search(query)

        log.info("Sample vector search run", query=query)
        for res in results:
            log.info("Vector search result", content=res.page_content, metadata=res.metadata)

# Run if this file is executed directly
if __name__ == "__main__":
    ingestion = DataIngestion()
    ingestion.run_pipeline()