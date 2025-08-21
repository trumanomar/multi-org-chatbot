from sentence_transformers import SentenceTransformer,util

# # تحميل الموديل من HuggingFace

# model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# # حفظه محلياً في مجلد
# model.save("./models/all-MiniLM-L6-v2")

# print("✅ تم تحميل وحفظ الموديل في ./models/all-MiniLM-L6-v2")
sentences = ["This is an example sentence", "Each sentence is converted"]

model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
model.save("./backend/multi_models/paraphrase-multilingual-MiniLM-L12-v2")
print("saved successfully /multi_models/paraphrase-multilingual-MiniLM-L12-v2")
