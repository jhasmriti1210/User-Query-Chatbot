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
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# OpenAI import
from langchain.chat_models import ChatOpenAI

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Folders
UPLOAD_FOLDER = "uploaded_docs"
INDEX_FOLDER = "faiss_indexes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(INDEX_FOLDER, exist_ok=True)

# Env-vars
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SYSTEM_PROMPT:
    raise ValueError("SYSTEM_PROMPT is not set in the .env file.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in the .env file.")

# Embeddings & LLM
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.0
)

def pdf_loader(pdf_path):
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    # enforce per-PDF page limit
    if len(docs) > 1000:
        raise ValueError(f"PDF has {len(docs)} pages; exceeds 1,000-page limit.")
    return docs

def text_chunking(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
    return splitter.split_documents(docs)

@app.route("/")
def home():
    return "Welcome to the RAG Pipeline service. Use /upload to upload up to 20 PDFs and /query to ask questions."

@app.route("/upload", methods=["POST"])
def upload_files():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded; use form-field name 'files'"}), 400
    if len(files) > 20:
        return jsonify({"error": "Maximum 20 documents allowed per upload."}), 400

    saved = []
    for file in files:
        filename = secure_filename(file.filename or "")
        if not filename:
            continue

        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)

        try:
            # load, chunk, index
            docs = pdf_loader(save_path)
            chunks = text_chunking(docs)

            faiss_index = FAISS.from_documents(chunks, embeddings)
            index_name = pathlib.Path(filename).stem
            index_path = os.path.join(INDEX_FOLDER, index_name)
            os.makedirs(index_path, exist_ok=True)
            faiss_index.save_local(index_path)

            saved.append(filename)

        except Exception as e:
            return jsonify({"error": f"Error processing '{filename}': {str(e)}"}), 500

    return jsonify({
        "message": "Upload and indexing successful.",
        "filenames": saved
    }), 200

@app.route("/query", methods=["POST"])
def query_uploaded():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    filename = data.get("filename", "").strip()

    if not question:
        return jsonify({"error": "Question is required."}), 400
    if not filename:
        return jsonify({"error": "Filename is required."}), 400

    index_name = pathlib.Path(filename).stem
    index_path = os.path.join(INDEX_FOLDER, index_name)
    if not os.path.exists(index_path):
        return jsonify({"error": "No such document indexed. Please upload first."}), 400

    try:
        faiss_index = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        retriever = faiss_index.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5}
        )

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
        answer = result.get("output", "")

        return jsonify({"answer": answer}), 200

    except Exception as e:
        return jsonify({"error": f"Error during query: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8082)