from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
import os
import re
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class RAGUtils:
    def __init__(self):
        self.documents = []
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = None
        self.pickle_file = 'rag/documents.pkl'
        self.load_documents()
    
    def load_documents(self):
        """Load documents from pickle file"""
        if os.path.exists(self.pickle_file):
            try:
                with open(self.pickle_file, 'rb') as f:
                    data = pickle.load(f)
                    self.documents = data.get('documents', [])
                    if self.documents:
                        self.tfidf_vectorizer = data.get('vectorizer')
                        self.tfidf_matrix = data.get('matrix')
            except Exception as e:
                print(f"Error loading documents: {e}")
                # If loading fails, initialize empty
                self.documents = []
                self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
                self.tfidf_matrix = None
    
    def save_documents(self):
        """Save documents to pickle file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.pickle_file), exist_ok=True)
            # Save only if we have documents
            if self.documents:
                data = {
                    'documents': self.documents,
                    'vectorizer': self.tfidf_vectorizer,
                    'matrix': self.tfidf_matrix
                }
                with open(self.pickle_file, 'wb') as f:
                    pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving documents: {e}")
    
    def process_document(self, file_path):
        """Process a document and add it to the collection"""
        # Determine loader based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            try:
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            except:
                return False
        elif ext == '.txt':
            try:
                loader = TextLoader(file_path)
                documents = loader.load()
            except:
                return False
        elif ext == '.docx':
            try:
                from langchain_community.document_loaders import Docx2txtLoader
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
            except:
                return False
        else:
            return False
        
        # Load and split document
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        
        # Add to documents collection
        for chunk in chunks:
            self.documents.append(chunk.page_content)
        
        # Update TF-IDF matrix
        if self.documents:
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(self.documents)
            # Save documents to pickle file
            self.save_documents()
        
        return True
    
    def retrieve_relevant_info(self, query, k=3):
        """Retrieve relevant information using TF-IDF"""
        if not self.documents or self.tfidf_matrix is None:
            return []
        
        # Transform query
        query_vector = self.tfidf_vectorizer.transform([query])
        
        # Calculate similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
        
        # Get top k indices
        top_indices = np.argsort(similarities)[-k:][::-1]
        
        # Return top k documents
        return [self.documents[i] for i in top_indices]

rag_utils = RAGUtils()
