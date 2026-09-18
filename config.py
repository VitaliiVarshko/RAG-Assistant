import chromadb
from chromadb.utils import embedding_functions

# Settings for embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# Chunk settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Languages
SUPPORTED_LANGUAGES = {
    "ru": {
        "name": "Russian",
        "collection": "documents_ru",
        "fallback": "ru"
    },
    "uk": {
        "name": "Ukrainian",
        "collection": "documents_uk",
        "fallback": "ru"
    }
}

# Function for creating a ChromaDB client
def get_chroma_client(db_path="./chroma_db"):
    client = chromadb.PersistentClient(path=db_path)
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    return client, embedding_function

# Function for getting or creating a collection
def get_collection(client, embedding_function, lang_code):
    collection_name = SUPPORTED_LANGUAGES[lang_code]["collection"]
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function
    )
    return collection