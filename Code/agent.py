import os, json
from pathlib import Path
from operator import itemgetter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

CHROMA_DIR = str(Path(__file__).parent / "chroma_db")

def make_chain():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vs = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    
    retriever = vs.as_retriever(search_kwargs={"k": 30})
    
    identity = "Nessun dato web."
    if Path("DATA/info_data.json").exists():
        with open("DATA/info_data.json", "r", encoding="utf-8") as f:
            identity = f.read().replace("{", "{{").replace("}", "}}")

    template = f"""Sei Doxa, un Agente AI Senior specializzato nell'analisi tecnica, legale ed economica di documentazione complessa (Aste Giudiziarie, Bandi e Appalti).
    La tua missione è estrarre la verità dai documenti fornendo risposte ultra-sintetiche, oggettive e di massima precisione.

    DATI WEB (Sintesi): 
    {identity}

    CONTESTO DOCUMENTALE (Dettaglio Tecnico): 
    {{context}}

    PROTOCOLLO OPERATIVO:
    1. SINTESI E PRECISIONE: Fornisci risposte asciutte, evita preamboli. Vai dritto al punto citando cifre, date e nomi.
    2. ANALISI ECONOMICA: Scansiona il contesto per ogni onere (sanatorie, debiti condominiali, spese straordinarie). Se trovi tabelle, analizzale riga per riga.
    3. STATO LEGALE E RISCHI: Identifica difformità urbanistiche, stato di occupazione, diritti di terzi o clausole limitative.
    4. PROTOCOLLO CITAZIONI: Ogni dato deve essere seguito dalla fonte esatta (es. "Perizia.pdf, pag. 12"). Se il dato proviene dal web, cita "Dati Web".
    5. ZERO ALLUCINAZIONI: Se un'informazione non è presente nel contesto o nei dati web, dichiara esplicitamente di non poter rispondere.
    """
    
    # Integriamo la memoria nel prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", template),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    # Organizziamo gli input: il retriever riceve solo la domanda attuale
    return (
        {
            "context": itemgetter("question") | retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)),
            "question": itemgetter("question"),
            "chat_history": itemgetter("chat_history")
        }
        | prompt 
        | ChatOpenAI(model="gpt-5.1", temperature=0) 
        | StrOutputParser()
    )
