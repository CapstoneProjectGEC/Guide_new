# Guide_new

## Karnataka Tourism Smart AI Guide Platform (Belur Chennakeshava Temple)

An AI-powered multimodal tourism platform dedicated to the UNESCO World Heritage Hoysala monument — **Sri Chennakeshava Temple at Belur**, Karnataka.

### Key Features
* **Bilingual Conversational AI (Kannada & English)**: Offline hybrid neural translation with NLLB-200, domain-hardened heritage glossary, and fact-preservation validation.
* **Evidence-Grounded RAG Engine**: Hybrid retrieval (Dense Semantic + BM25 Lexical + Cross-Encoder Reranking) backed by ChromaDB and official archaeological archives with strict zero-hallucination guarantees.
* **Interactive 3D Precinct Exploration**: Photorealistic procedural 3D precinct map of the entire 18 UNESCO complex monuments and 6 architectural zones built with Three.js.
* **Multimodal Voice Assistance**: Offline Text-to-Speech (Piper ONNX) and Speech-to-Text for spoken heritage inquiries.
* **Comprehensive Administrative Suite**: Document management, knowledge base synchronization, and health diagnostics dashboard.

### Quick Start
To launch all services (MySQL, Ollama, Backend REST API, and Frontend Web UI):
* Run `run.bat` or `powershell -ExecutionPolicy Bypass -File .\run.ps1`
* **Frontend Web UI**: http://127.0.0.1:3000
* **Backend API Docs (Swagger)**: http://127.0.0.1:8000/docs
