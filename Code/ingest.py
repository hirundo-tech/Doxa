import os, json, shutil
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from llama_parse import LlamaParse

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "DATA"
CHROMA_DIR = str(BASE_DIR / "chroma_db")

def parse_pdf_with_tables(file_path: Path):
    parser = LlamaParse(result_type="markdown", num_workers=4, language="it")
    llama_docs = parser.load_data(str(file_path))
    return [Document(page_content=d.text, metadata={"source": file_path.name, "page": i+1}) for i, d in enumerate(llama_docs)]

def run_ingest():
    if Path(CHROMA_DIR).exists(): shutil.rmtree(CHROMA_DIR)
    docs = []
    for p in DATA_DIR.glob("*"):
        if p.suffix.lower() == ".pdf": docs.extend(parse_pdf_with_tables(p))
        elif p.name == "info_data.json":
            with open(p, "r", encoding="utf-8") as f:
                docs.append(Document(page_content=f.read(), metadata={"source": "info_data.json"}))
    
    # CONFIGURAZIONE GOLDEN AGE
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000, 
        chunk_overlap=500, 
        separators=["\n## ", "\n### ", "\n\n", "\n", " "]
    )
    chunks = splitter.split_documents(docs)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=CHROMA_DIR)
    return True
