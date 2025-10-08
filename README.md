# 🧠 Multi-Org Chatbot with RAG

A multi-organization RAG (Retrieval-Augmented Generation) system with complete data isolation, role-based access control, and intelligent document querying powered by Ollama 3.1 8B Instruct and knowledge graphs.

![Multi-Org Chatbot Banner](https://via.placeholder.com/1200x300/5B6FA8/FFFFFF?text=Multi-Org+Chatbot+RAG)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Database Architecture](#database-architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [User Roles](#user-roles)
- [MCP Integration](#mcp-integration)
- [Knowledge Graph](#knowledge-graph)
- [Screenshots](#screenshots)
- [Project Structure](#project-structure)
- [Team](#team)

## 🌟 Overview

Multi-Org Chatbot is an enterprise-grade RAG system that enables multiple organizations to securely manage and query their documents using natural language. The system leverages Ollama 3.1 8B Instruct for intelligent responses, ChromaDB for vector embeddings, and automatically builds knowledge graphs from document entities to provide context-aware answers with confidence scoring.

## ✨ Features

### 🔐 Multi-Organization Support
- Complete data isolation between organizations (domains)
- Organization-level document and user management
- Secure domain-based data segregation

### 👥 Role-Based Access Control (RBAC)
- **Super Admin**: Manages all organizations, creates admins across domains
- **Admin**: Manages users and documents within their organization
- **User**: Access to chat interface and document querying

### 🤖 Intelligent Document Processing
- **Docling MCP**: Advanced document chunking and text extraction
- **MySQL MCP**: Query-based data retrieval for answering questions
- **MySQL (Standard)**: Authentication, document metadata, and chunk storage
- **ChromaDB**: Vector embeddings for semantic search
- **Ollama 3.1 8B Instruct**: LLM for answer generation with confidence scores

### 🕸️ Knowledge Graph Generation
- Automatic entity extraction from document chunks
- Triplet generation (subject-predicate-object) using Ollama
- Graph DB storage for relationship mapping
- Enhanced context retrieval through entity relationships

### 💬 Smart Chat Interface
- Multi-session chat management
- Source citations with document references
- Confidence-based response scoring
- User feedback system for response quality
- Real-time context-aware conversations

### 📄 Document Management
- Support for PDF, DOCX, and text files
- Automatic chunking with configurable parameters
- Document activation/deactivation
- Chunk visualization and management
- Entity-based search and retrieval

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Flutter Frontend                      │
│              (Web - Chrome Port 5000)                    │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST API
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│                 (uvicorn app.main:app)                   │
└─────┬───────────────┬───────────────┬───────────────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────────┐
│  MySQL   │   │ ChromaDB │   │  Graph DB    │
│  (Auth   │   │ (Vector  │   │  (Knowledge  │
│  + Meta) │   │ Storage) │   │   Graph)     │
└──────────┘   └──────────┘   └──────────────┘
      │
      │
┌─────┴───────────────────────────────────────────────────┐
│                    MCP Servers Layer                     │
├──────────────┬─────────────────┬────────────────────────┤
│  Docling MCP │  MySQL MCP      │   Graph DB MCP         │
│  (Chunking)  │  (Queries)      │   (Entities/Triplets)  │
└──────────────┴─────────────────┴────────────────────────┘
                     │
                     ▼
              ┌─────────────┐
              │   Ollama    │
              │  3.1 8B     │
              │  Instruct   │
              └─────────────┘
```

## 🗄️ Database Architecture

### Entity Relationship Diagram

```mermaid
erDiagram
    DOMAINS ||--o{ USERS : contains
    DOMAINS ||--o{ DOCUMENTS : owns
    USERS ||--o{ CHAT_SESSIONS : creates
    CHAT_SESSIONS ||--o{ MESSAGES : contains
    DOCUMENTS ||--o{ CHUNKS : divided_into
    CHUNKS ||--o{ ENTITIES : extracted_from
    ENTITIES ||--o{ TRIPLETS : forms
    MESSAGES ||--o{ FEEDBACK : receives
    MESSAGES }o--o{ CHUNKS : references

    DOMAINS {
        int id PK
        string name UK
        boolean is_active
        timestamp created_at
    }

    USERS {
        int id PK
        string username UK
        string email UK
        string hashed_password
        enum role "super_admin, admin, user"
        int domain_id FK
        timestamp created_at
    }

    DOCUMENTS {
        int id PK
        string filename
        string file_path
        int domain_id FK
        int uploaded_by FK
        boolean is_active
        timestamp created_at
        int chunk_count
    }

    CHUNKS {
        int id PK
        int document_id FK
        text content
        int chunk_index
        json metadata
        timestamp created_at
    }

    ENTITIES {
        int id PK
        int chunk_id FK
        string entity_text
        string entity_type "PERSON, ORG, DATE, etc"
        timestamp extracted_at
    }

    TRIPLETS {
        int id PK
        int entity_id FK
        string subject
        string predicate
        string object
        float confidence_score
        timestamp created_at
    }

    CHAT_SESSIONS {
        int id PK
        int user_id FK
        string session_name
        timestamp created_at
        timestamp last_activity
    }

    MESSAGES {
        int id PK
        int session_id FK
        enum role "user, assistant"
        text content
        json source_chunks "Array of chunk IDs"
        float confidence_score
        timestamp created_at
    }

    FEEDBACK {
        int id PK
        int message_id FK
        int user_id FK
        int rating "1-5 stars"
        text comment
        timestamp created_at
    }
```

### Database Details

#### MySQL Databases

**1. Main Application Database (`chatbot_rag`)**
- **Purpose**: Authentication, document management, chat history
- **Tables**: `domains`, `users`, `documents`, `chunks`, `chat_sessions`, `messages`, `feedback`
- **Access**: Direct SQLAlchemy ORM
- **Created via**: `python -m app.DB.create_table`

**2. MySQL MCP Server**
- **Purpose**: Query-based information retrieval
- **Access**: Through MCP protocol for answering queries
- **Use Case**: Structured data queries (e.g., "How many appointments?", "What's the average rating?")

#### Vector Database
- **ChromaDB**: Stores document embeddings for semantic similarity search

#### Graph Database
- **Purpose**: Store entity relationships and triplets
- **Data**: Entities extracted from chunks → Triplets (subject-predicate-object)
- **Generation**: Ollama 3.1 8B Instruct analyzes chunks to create relationships

## 🛠️ Tech Stack

### Frontend
- **Flutter 3.0+**: Cross-platform UI framework
- **Dart**: Programming language
- **Material Design**: UI components
- **Port**: 5000 (Chrome)

### Backend
- **FastAPI**: High-performance async Python web framework
- **Python 3.10+**: Core programming language
- **Uvicorn**: ASGI server
- **SQLAlchemy**: ORM for database operations
- **Pydantic**: Data validation

### AI & Data Layer
- **Ollama 3.1 8B Instruct**: Local LLM for answer generation and triplet extraction
- **ChromaDB**: Vector database for semantic search
- **MySQL 8.0+**: Relational database (dual purpose: app data + MCP queries)
- **Graph Database**: Knowledge graph storage for entities and relationships

### MCP Servers
- **Docling MCP**: Document chunking and text extraction
- **MySQL MCP**: Database query service for Q&A
- **Graph DB MCP**: Entity and triplet management

## 📦 Prerequisites

- **Python 3.10+**
- **Flutter SDK 3.0+**
- **MySQL 8.0+**
- **Ollama** (with llama3.1:8b-instruct model)
- **Git**
- **Node.js** (for MCP servers)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/youssefelzahar/multi-org-chatbot
cd multi-org-chatbot
git checkout db_mcp
```

### 2. Database Setup

```bash
# Create MySQL database
mysql -u root -p

CREATE DATABASE chatbot_rag;
EXIT;
```

### 3. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create database tables
python -m app.DB.create_table

# Set up environment variables
cp .env.example .env
# Edit .env with your MySQL credentials and other configs
```

### 4. Install Ollama Model

```bash
# Install Ollama 3.1 8B Instruct
ollama pull llama3.1:8b-instruct

# Verify installation
ollama list
```

### 5. Start MCP Servers

```bash
cd backend

# Start all MCP servers (Docling, MySQL MCP, Graph DB)
python start_mcp_servers.py
```

### 6. Frontend Setup

```bash
cd frontend

# Install Flutter dependencies
flutter pub get

# Verify Flutter installation
flutter doctor
```

## 💻 Usage

### Start the Backend

```bash
cd backend

# Ensure virtual environment is activated
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Start FastAPI server with hot reload
uvicorn app.main:app --reload

# API will be available at http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Start MCP Servers

```bash
cd backend

# Start all MCP servers in separate processes
python start_mcp_servers.py

# This starts:
# - Docling MCP (document chunking)
# - MySQL MCP (query service)
# - Graph DB MCP (entity/triplet management)
```

### Start the Frontend

```bash
cd frontend

# Run on Chrome (port 5000)
flutter run -d chrome --web-port 5000

# Access at: http://localhost:5000
```

### Complete Startup Sequence

```bash
# Terminal 1: Database
mysql -u root -p
# Ensure chatbot_rag database exists

# Terminal 2: Backend
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn app.main:app --reload

# Terminal 3: MCP Servers
cd backend
python start_mcp_servers.py

# Terminal 4: Frontend
cd frontend
flutter run -d chrome --web-port 5000
```

## 👤 User Roles

### Super Admin
- **Capabilities**:
  - Create and manage all organizations (domains)
  - Create admins for any organization
  - View global statistics (total orgs, admins, documents)
  - Activate/deactivate domains
  - Monitor system-wide activity
  - Access to all features across domains

### Admin
- **Capabilities**:
  - Manage users within their organization
  - Create new users (restricted to their domain)
  - Upload and manage documents
  - View document chunks
  - Activate/deactivate documents
  - View organization-specific statistics
  - Monitor user feedback

### User
- **Capabilities**:
  - Access chat interface
  - Create and manage chat sessions
  - Query documents within their organization
  - View chat history
  - Rate AI responses
  - View source documents for answers

## 🔌 MCP Integration

### Model Context Protocol (MCP) Servers

#### 1. Docling MCP Server
**Purpose**: Document processing and chunking

**Capabilities**:
- Parse PDF, DOCX, and text files
- Extract text with layout preservation
- Split documents into semantic chunks
- Handle tables, images, and structured content
- Configurable chunk size and overlap

**Configuration**:
```json
{
  "chunk_size": 512,
  "chunk_overlap": 50,
  "separator": "\n\n"
}
```

#### 2. MySQL MCP Server
**Purpose**: Query-based data retrieval for Q&A

**Capabilities**:
- Execute natural language queries against structured data
- Return aggregated statistics (counts, averages, etc.)
- Join multiple tables for complex queries
- Provide context for LLM responses

**Example Queries**:
- "How many spa appointments do we have today?"
- "What's the average guest satisfaction rating?"
- "List all services offered"

#### 3. Graph DB MCP Server
**Purpose**: Entity and relationship management

**Capabilities**:
- Store entities extracted from document chunks
- Manage triplets (subject-predicate-object relationships)
- Query knowledge graph for related entities
- Enhance context retrieval through relationships

**Workflow**:
```
Document → Chunks → Entity Extraction → Triplet Generation → Graph Storage
```

### Starting MCP Servers

The `start_mcp_servers.py` script launches all MCP servers:

```python
# backend/start_mcp_servers.py
import subprocess
import sys

def start_servers():
    servers = [
        {"name": "Docling", "command": ["python", "mcp_servers/docling_server.py"]},
        {"name": "MySQL", "command": ["python", "mcp_servers/mysql_server.py"]},
        {"name": "Graph DB", "command": ["python", "mcp_servers/graph_server.py"]}
    ]
    
    processes = []
    for server in servers:
        print(f"Starting {server['name']} MCP server...")
        proc = subprocess.Popen(server['command'])
        processes.append(proc)
    
    return processes
```

## 🕸️ Knowledge Graph

### Entity Extraction & Triplet Generation

The system automatically builds a knowledge graph from documents:

#### 1. Entity Extraction
When a document is uploaded and chunked:
- Each chunk is analyzed by Ollama 3.1 8B Instruct
- Named entities are identified (PERSON, ORG, LOCATION, DATE, etc.)
- Entities are stored with their type and chunk reference

#### 2. Triplet Generation
For each chunk with entities:
- Ollama generates relationship triplets
- Format: (Subject) - [Predicate] → (Object)
- Example: (John Smith) - [works_at] → (Acme Corp)
- Confidence scores assigned to each triplet

#### 3. Graph Storage
Triplets are stored in Graph DB:
```
ENTITY_NODE -[RELATIONSHIP]-> ENTITY_NODE
```

#### 4. Query Enhancement
When answering questions:
- Relevant entities identified from user query
- Graph traversed to find related entities
- Additional context retrieved from related chunks
- Enhanced prompt sent to Ollama

### Example Knowledge Graph

```
Document: "Hotel Amenities Guide.pdf"

Entities Extracted:
- "Luxury Grand Hotel" (ORG)
- "spa services" (SERVICE)
- "massages" (SERVICE)
- "facials" (SERVICE)
- "body treatments" (SERVICE)

Triplets Generated:
1. (Luxury Grand Hotel) -[offers]-> (spa services) [confidence: 0.95]
2. (spa services) -[includes]-> (massages) [confidence: 0.92]
3. (spa services) -[includes]-> (facials) [confidence: 0.92]
4. (spa services) -[includes]-> (body treatments) [confidence: 0.90]

Graph Visualization:
┌──────────────────────┐
│ Luxury Grand Hotel   │
└──────────┬───────────┘
           │ offers
           ▼
     ┌─────────────┐
     │spa services │
     └──────┬──────┘
            │ includes
       ┌────┴────┬──────────┐
       ▼         ▼          ▼
  ┌────────┐ ┌────────┐ ┌────────────────┐
  │massages│ │facials │ │body treatments │
  └────────┘ └────────┘ └────────────────┘
```
you can find files  to test on backend/app/hotel
and questions to test on backend/app/readme.md
## 📸 Screenshots

### Authentication
![Login Page](./screenshots/login.png)
*Secure authentication with username and password*

---

### Super Admin Dashboard
![Super Admin Dashboard](./screenshots/super_admin_dashboard.png)
*Global overview: Organizations, Admins, and Documents*

![Domains Management](./screenshots/domains_list.png)
*View and manage all organization domains*

![Create Domain](./screenshots/create_domain.png)
*Simple organization creation interface*

![Create Admin](./screenshots/create_admin.png)
*Assign admins to specific organizations*

---

### Admin Dashboard
![Admin Dashboard](./screenshots/admin_dashboard.png)
*Organization-specific dashboard with users and documents count*

![User Management](./screenshots/users_list.png)
*Manage users within the organization*

![Create User](./screenshots/create_user.png)
*Add new users with role assignment (domain-restricted)*

![Document Management](./screenshots/documents_list.png)
*Upload, activate, and manage documents with chunk counts*

![Upload Documents](./screenshots/upload_document.png)
*Drag-and-drop document upload interface*

![View Chunks](./screenshots/view_chunks.png)
*Inspect document chunks and extracted entities*

![Feedback System](./screenshots/feedback_list.png)
*Review user feedback and response ratings*

---

### User Interface
![Chat Interface](./screenshots/chat_interface.png)
*Clean chat UI for document querying*

![Chat with Sources](./screenshots/chat_with_sources.png)
*AI responses with source citations and confidence scores*

![Multiple Sessions](./screenshots/chat_sessions.png)
*Manage multiple conversation sessions*

![Rate Response](./screenshots/rate_response.png)
*User feedback system with star ratings*

## 📁 Project Structure

```
multi-org-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── config.py                  # Configuration settings
│   │   ├── DB/
│   │   │   ├── create_table.py        # Database table creation script
│   │   │   └── connection.py          # Database connection management
│   │   ├── models/                    # SQLAlchemy models
│   │   │   ├── domain.py              # Domains/Organizations model
│   │   │   ├── user.py                # Users model with RBAC
│   │   │   ├── document.py            # Documents model
│   │   │   ├── chunk.py               # Document chunks model
│   │   │   ├── entity.py              # Extracted entities model
│   │   │   ├── triplet.py             # Knowledge graph triplets
│   │   │   ├── chat_session.py        # Chat sessions model
│   │   │   ├── message.py             # Chat messages model
│   │   │   └── feedback.py            # User feedback model
│   │   ├── routes/                    # API route handlers
│   │   │   ├── auth.py                # Authentication endpoints
│   │   │   ├── domains.py             # Domain management
│   │   │   ├── users.py               # User management
│   │   │   ├── documents.py           # Document upload/management
│   │   │   ├── chat.py                # Chat interface
│   │   │   └── feedback.py            # Feedback endpoints
│   │   ├── services/                  # Business logic
│   │   │   ├── auth_service.py        # Authentication logic
│   │   │   ├── rag_service.py         # RAG pipeline
│   │   │   ├── chunking_service.py    # Document chunking
│   │   │   ├── embedding_service.py   # Vector embeddings
│   │   │   ├── entity_service.py      # Entity extraction
│   │   │   ├── triplet_service.py     # Triplet generation
│   │   │   └── ollama_service.py      # Ollama integration
│   │   ├── schemas/                   # Pydantic schemas
│   │   │   ├── user.py                # User request/response models
│   │   │   ├── document.py            # Document schemas
│   │   │   ├── chat.py                # Chat schemas
│   │   │   └── feedback.py            # Feedback schemas
│   │   └── utils/                     # Utility functions
│   │       ├── auth.py                # JWT token handling
│   │       ├── dependencies.py        # FastAPI dependencies
│   │       └── exceptions.py          # Custom exceptions
│   ├── mcp_servers/                   # MCP server implementations
│   │   ├── docling_server.py          # Docling MCP for chunking
│   │   ├── mysql_server.py            # MySQL MCP for queries
│   │   └── graph_server.py            # Graph DB MCP
│   ├── start_mcp_servers.py           # MCP servers launcher
│   ├── requirements.txt               # Python dependencies
│   └── .env                           # Environment variables
├── frontend/
│   ├── lib/
│   │   ├── main.dart                  # Flutter app entry point
│   │   ├── screens/                   # UI screens
│   │   │   ├── auth/
│   │   │   │   └── login_screen.dart
│   │   │   ├── super_admin/
│   │   │   │   ├── dashboard.dart
│   │   │   │   ├── domains_screen.dart
│   │   │   │   └── create_admin.dart
│   │   │   ├── admin/
│   │   │   │   ├── dashboard.dart
│   │   │   │   ├── users_screen.dart
│   │   │   │   ├── documents_screen.dart
│   │   │   │   └── feedback_screen.dart
│   │   │   └── user/
│   │   │       └── chat_screen.dart
│   │   ├── widgets/                   # Reusable widgets
│   │   │   ├── sidebar.dart
│   │   │   ├── chat_bubble.dart
│   │   │   └── document_card.dart
│   │   ├── models/                    # Data models
│   │   │   ├── user.dart
│   │   │   ├── document.dart
│   │   │   └── message.dart
│   │   ├── services/                  # API services
│   │   │   ├── api_service.dart
│   │   │   ├── auth_service.dart
│   │   │   └── chat_service.dart
│   │   └── utils/                     # Utility functions
│   │       ├── constants.dart
│   │       └── validators.dart
│   ├── pubspec.yaml                   # Flutter dependencies
│   └── assets/                        # Static assets
├── docs/                              # Additional documentation
├── tests/                             # Test suites
└── README.md                          # This file
```

## 🔧 Configuration

### Backend Configuration (`.env`)

```bash
# Database
DATABASE_URL=mysql://user:password@localhost:3306/chatbot_rag
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=chatbot_rag

# JWT Authentication
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Ollama
OLLAMA_HOST=http://localhost:11434/v1
OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_COLLECTION=document_embeddings

# MCP Servers
DOCLING_MCP_PORT=5001
MYSQL_MCP_PORT=5002
GRAPH_MCP_PORT=5003

# RAG Settings
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_RESULTS=5
CONFIDENCE_THRESHOLD=0.7
```

### Frontend Configuration

Update `lib/utils/constants.dart`:
```dart
class ApiConstants {
  static const String baseUrl = 'http://localhost:8000';
  static const String apiVersion = '/api/v1';
}
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend
flutter test
```

## 🔒 Security Features

- **JWT-based Authentication**: Secure token-based auth
- **Role-Based Access Control**: Hierarchical permissions
- **Data Isolation**: Organization-level data segregation
- **Password Hashing**: bcrypt for secure password storage
- **Input Validation**: Pydantic schemas for data validation
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **API Rate Limiting**: Prevent abuse
- **CORS Configuration**: Controlled cross-origin access

## 👥 Team

This project was developed during a **Full Stack Data Scientist Internship** at **Fixed Solutions** by:

- **youssef elzahar** - Full Stack Data Scientist
- **Mohamed Khaled** - Full Stack Data Scientist
- **Omar Dawoud** - Full Stack Data Scientist

### Acknowledgments

Special thanks to **Fixed Solutions** for providing the opportunity, resources, and mentorship throughout this internship project.

## 🗺️ Roadmap

- [ ] Multi-language document support
- [ ] Advanced graph visualization dashboard
- [ ] Real-time collaboration features
- [ ] Export chat history as PDF
- [ ] Custom entity type definitions
- [ ] Batch document upload
- [ ] Mobile app (iOS/Android)
- [ ] Integration with more LLM providers
- [ ] Advanced analytics and insights
- [ ] Webhook integrations



## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


## 🔗 Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Flutter Documentation](https://docs.flutter.dev)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [ChromaDB Documentation](https://docs.trychroma.com)

---

**Built with ❤️ by youssef elzahar, Mohamed Khaled, and Omar Dawoud**

**Developed during Full Stack Data Scientist Internship at Fixed Solutions**