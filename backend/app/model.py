from sentence_transformers import SentenceTransformer

# تحميل الموديل من HuggingFace
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# حفظه محلياً في مجلد
model.save("./models/all-MiniLM-L6-v2")

print("✅ تم تحميل وحفظ الموديل في ./models/all-MiniLM-L6-v2")
