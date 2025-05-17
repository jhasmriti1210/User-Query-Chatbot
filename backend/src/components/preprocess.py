from langchain.text_splitter import RecursiveCharacterTextSplitter 
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.embeddings import HuggingFaceEmbeddings

from typing import List
from langchain.docstore.document import Document
import os

# Load a single PDF or all PDFs from directory
def pdf_loader(pdf_path: str) -> List[Document]:
    try:
        if os.path.isfile(pdf_path):
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
        elif os.path.isdir(pdf_path):
            loader = DirectoryLoader(pdf_path, glob='*.pdf', loader_cls=PyPDFLoader)
            docs = loader.load()
        else:
            raise FileNotFoundError(f"Path {pdf_path} does not exist.")
        
        if not docs:
            raise ValueError("No PDF content found.")
        return docs

    except Exception as e:
        print(f"Error loading PDFs: {e}")
        return []

def text_chunking(extracted_docs: List[Document]) -> List[Document]:
    chunker = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    return chunker.split_documents(extracted_docs)

def hf_embeds() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2')
