# open mysql workbench 
  create database chatbot_rag;
# on terminal 
   cd backend
   python - m app.DB.create_table
# to run fastapi
   uvicorn app.main:app --reload
# to run frontend
  cd frontend
  flutter run -d chrome --web-port 5000




