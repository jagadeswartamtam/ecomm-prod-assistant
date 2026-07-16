from typing import List
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore
from prod_assistant.utils.model_loader import ModelLoader
from prod_assistant.config.settings import settings



class DataIngestion:

    def __init__(self, csv_dir, collection_name, embedding_model):
        self.csv_dir = csv_dir
        self.collection_name = collection_name
        self.embedding_model = embedding_model

    

    def _get_csv_path(self):
        """
        Returns the path of the CSV file to be ingested.
        """
        pass

    def _load_csv(self, csv_path):
        """
        Loads data from the CSV file.

        Args:
            csv_path (str): Path to the CSV file.

        Returns:
            DataFrame or list of records
        """
        pass

    
    

    def transform_data(self):
        """
        Loads the CSV, cleans the data,
        and prepares documents for ingestion.

        Returns:
            Processed documents.
        """
        pass

    def store_in_vector_db(self, documents):
        """
        Stores embedded documents in the vector database.

        Args:
            documents: Processed documents.
        """
        pass

    def run_pipeline(self):
        """
        Executes the complete data ingestion pipeline.
        """
        pass