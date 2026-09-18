import chromadb
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("documents_uk")

print(f"Collection: {collection.name}")
print(f"Documents: {collection.count()}")

# View the first 5 documents
all_docs = collection.get()
for i in range(min(5, len(all_docs['ids']))):
    print(f"\nID: {all_docs['ids'][i]}")
    print(f"Text: {all_docs['documents'][i][:200]}...")
    print(f"Metadata: {all_docs['metadatas'][i]}")