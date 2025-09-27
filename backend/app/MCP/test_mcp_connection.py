from ..utilis.docling_client import DoclingHttpClient

if __name__ == "__main__":
    client = DoclingHttpClient("http://127.0.0.1:5000")
    chunks = client.load_and_split(
        file_path=r"C:\Users\youss\OneDrive\Desktop\multi-org-chatbot\backend\test.xlsx"
, 
        chunk_size=300, 
        chunk_overlap=50
    )
    print(f"Type of chunks: {type(chunks)}")
    print(f"Content of chunks: {chunks}")

    for i, chunk in enumerate(chunks[:3]): 
        print(f"\n--- Chunk {i+1} ---")
        print(chunk["page_content"][:200], "...")
