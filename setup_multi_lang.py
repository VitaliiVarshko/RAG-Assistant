import chromadb
from chromadb.utils import embedding_functions

# Connecting to the database
client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Creating new collections for languages
collections = {
    "ru": client.get_or_create_collection(
        name="documents_ru",
        embedding_function=embedding_function
    ),
    "uk": client.get_or_create_collection(
        name="documents_uk",
        embedding_function=embedding_function
    )
}

print("✅ Created collections:")
for lang, col in collections.items():
    print(f"   {lang.upper()}: {col.name} (documents: {col.count()})")

# Showing all collections in the DB
print("\n📊 All collections in the DB:")
for col in client.list_collections():
    print(f"   - {col.name}")