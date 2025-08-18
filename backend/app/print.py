from VectorDB.DB import vectorstore

count = vectorstore._collection.count()
print(f"Total vectors: {count}")

results = vectorstore.similarity_search("", k=3)
for r in results:
    print(r.page_content)