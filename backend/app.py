import os
import pathlib
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)



UPLOAD_FOLDER = "uploaded_docs"
INDEX_FOLDER = "faiss_indexes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_FOLDER, exist_ok=True)

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not SYSTEM_PROMPT:
    raise ValueError("SYSTEM_PROMPT is not set in the .env file.")

if not HF_TOKEN:
    raise ValueError("HUGGINGFACEHUB_API_TOKEN is not set in the .env file.")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set in the .env file.")

# Initialize HuggingFace embeddings
embeddings = HuggingFaceEmbeddings(
    model_name='sentence-transformers/all-mpnet-base-v2'
)

# Initialize Gemini LLM (Google Generative AI)
llm = ChatGoogleGenerativeAI(model="models/chat-bison-001", google_api_key=GEMINI_API_KEY)


def pdf_loader(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    if not docs:
        raise ValueError("No content found in PDF")
    return docs

def text_chunking(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    return splitter.split_documents(docs)

@app.route("/")
def home():
    return "Welcome to the Medical Chatbot backend. Use /upload to upload PDFs and /query to ask questions."

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    if filename == "":
        return jsonify({"error": "Empty filename"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(save_path)

    try:
        docs = pdf_loader(save_path)
        chunks = text_chunking(docs)

        faiss_index = FAISS.from_documents(chunks, embeddings)
        index_name = pathlib.Path(filename).stem
        index_path = os.path.join(INDEX_FOLDER, index_name)
        os.makedirs(index_path, exist_ok=True)
        faiss_index.save_local(index_path)

        return jsonify({
            "message": "Upload and indexing successful.",
            "filename": filename
        }), 200

    except Exception as e:
        return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500

@app.route("/query", methods=["POST"])
def query_uploaded():
    data = request.get_json()
    question = data.get("question", "").strip()
    filename = data.get("filename", "").strip()

    if not question:
        return jsonify({"error": "Question is required"}), 400
    if not filename:
        return jsonify({"error": "Filename is required"}), 400

    index_name = pathlib.Path(filename).stem
    index_path = os.path.join(INDEX_FOLDER, index_name)

    if not os.path.exists(index_path):
        return jsonify({"error": "No document found. Please upload it first."}), 400

    try:
        faiss_index = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
        retriever = faiss_index.as_retriever(search_type="similarity", search_kwargs={"k": 5})

        prompt_template = (
            SYSTEM_PROMPT + "\n\n"
            "Use the following CONTEXT to answer the question. "
            "If the answer is not in the context, say 'I don't know.'\n\n"
            "CONTEXT:\n{context}\n\n"
            "Question: {input}\n"
            "Answer:"
        )
        prompt = ChatPromptTemplate.from_template(prompt_template)

        qa_chain = create_stuff_documents_chain(
            llm=llm,
            prompt=prompt,
            document_variable_name="context"
        )
        rag_chain = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=qa_chain
        )

        result = rag_chain.invoke({"input": question})

        answer = result.get("output", "")  # sometimes the key is "output"

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"error": f"Error during query: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8082)
