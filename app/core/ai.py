import os
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF
import tabula
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

AI_UNAVAILABLE = "AI_UNAVAILABLE"


class DocumentProcessor:
    """Handles PDF processing including text, tables, and metadata extraction"""
    
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def extract_text_with_metadata(self, pdf_path: Path) -> List[Document]:
        """Extract text from PDF with page numbers and source metadata"""
        documents = []
        pdf_document = fitz.open(pdf_path)
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text = page.get_text()
            
            if text.strip():
                # Extract text coordinates for highlighting (bounding boxes)
                blocks = page.get_text("blocks")
                text_blocks = []
                
                for block in blocks:
                    if block[6] == 0:  # Text block
                        text_blocks.append({
                            "text": block[4],
                            "bbox": list(block[:4])  # x0, y0, x1, y1
                        })
                
                # Create document with rich metadata
                doc = Document(
                    page_content=text,
                    metadata={
                        "source": pdf_path.name,
                        "page": page_num + 1,
                        "total_pages": len(pdf_document),
                        "file_path": str(pdf_path),
                        "text_blocks": json.dumps(text_blocks)  # For highlighting
                    }
                )
                documents.append(doc)
        
        pdf_document.close()
        return documents
    
    def extract_tables(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract tables from PDF using tabula"""
        try:
            tables = tabula.read_pdf(
                str(pdf_path),
                pages='all',
                multiple_tables=True,
                silent=True
            )
            
            extracted_tables = []
            for idx, table in enumerate(tables):
                if isinstance(table, pd.DataFrame) and not table.empty:
                    extracted_tables.append({
                        "table_index": idx,
                        "source": pdf_path.name,
                        "data": table.to_dict('records'),
                        "columns": list(table.columns),
                        "csv_string": table.to_csv(index=False)
                    })
            
            return extracted_tables
        except Exception as e:
            print(f"Table extraction failed for {pdf_path.name}: {str(e)}")
            print("Note: Table extraction requires Java. Install Java and set JAVA_HOME if needed.")
            return []
    
    def extract_images_info(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """Extract information about images in the PDF"""
        pdf_document = fitz.open(pdf_path)
        images_info = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images()
            
            for img_idx, img in enumerate(image_list):
                images_info.append({
                    "source": pdf_path.name,
                    "page": page_num + 1,
                    "image_index": img_idx,
                    "xref": img[0]
                })
        
        pdf_document.close()
        return images_info
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks while preserving metadata"""
        chunks = self.text_splitter.split_documents(documents)
        return chunks


class LLMManager:
    """Manages the configured LLM provider."""
    
    def __init__(self, llm_provider: str = "gemini", llm_model: Optional[str] = None):
        self.llm_provider = llm_provider.lower()
        self.llm_model = llm_model
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the selected LLM."""
        if self.llm_provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")

            model_name = self.llm_model or "gemini-3.8-flash"
            print(f"Initializing Gemini with model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.3,
                max_tokens=2048,
                max_retries=0,
                timeout=30,
            )

        if self.llm_provider != "openai":
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # OpenAI model mapping
        OPENAI_MODEL_MAP = {
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "gpt-4": "gpt-4",
            "gpt-4-turbo": "gpt-4-turbo-preview",
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini"
        }
        
        # Default to gpt-3.5-turbo (fastest and cheapest)
        default_model = "gpt-3.5-turbo"
        model_name = self.llm_model or default_model
        api_model_name = OPENAI_MODEL_MAP.get(model_name, default_model)
        
        if model_name not in OPENAI_MODEL_MAP:
            print(f"Warning: Unknown OpenAI model '{model_name}'. Defaulting to '{default_model}'.")
        
        print(f"Initializing ChatOpenAI with model: {api_model_name}")
        
        try:
            return ChatOpenAI(
                model=api_model_name,
                openai_api_key=api_key,
                temperature=0.3,
                max_tokens=2048,
                max_retries=0,
                timeout=30,
            )
        except Exception as e:
            print(f"Error initializing OpenAI: {str(e)}")
            raise
    
    def generate_response(self, prompt: str) -> str:
        """Generate a response from the LLM"""
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self.llm.invoke, prompt)
        try:
            response = future.result(timeout=30)
            # ChatOpenAI returns a message object with .content
            return response.content if hasattr(response, 'content') else str(response)
        except FutureTimeoutError:
            future.cancel()
            return AI_UNAVAILABLE
        except Exception as e:
            error_text = str(e)
            if "429" in error_text or "ResourceExhausted" in error_text or "quota" in error_text.lower():
                return AI_UNAVAILABLE

            if (
                "timeout" in error_text.lower()
                or "timed out" in error_text.lower()
                or "deadline exceeded" in error_text.lower()
            ):
                return AI_UNAVAILABLE

            print(f"LLM request failed: {error_text}")
            return AI_UNAVAILABLE
        finally:
            executor.shutdown(wait=False, cancel_futures=True)


class ProactiveInsights:
    """Generate local document insights without external API calls."""

    def local_insights(self, documents: List[Document]) -> Dict[str, Any]:
        """Create upload insights without making an external API request."""
        combined_text = " ".join(
            doc.page_content.replace("\n", " ").strip()
            for doc in documents[:5]
        ).strip()
        summary = combined_text[:500]
        if len(combined_text) > 500:
            summary = summary.rsplit(" ", 1)[0].rstrip() + "..."

        return {
            "summary": summary or "The collection is ready for questions.",
            "key_concepts": [],
            "suggested_questions": [],
            "document_stats": {
                "total_documents": len(set(doc.metadata.get("source") for doc in documents)),
                "total_pages": len(documents),
            },
        }


class EnhancedRAGSystem:
    """Enhanced Retrieval-Augmented Generation system with multi-document support"""
    
    def __init__(self, llm_provider: str = "gemini", llm_model: Optional[str] = None):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.llm_manager = LLMManager(llm_provider, llm_model)
        self.document_processor = DocumentProcessor()
        self.insights_generator = ProactiveInsights()
        self.vector_store = None
        self.tables_data = []
        self.images_info = []
    
    def process_files(
        self, 
        file_paths: List[Path], 
        vector_store_path: Path
    ) -> Dict[str, Any]:
        """Process multiple PDF files and create vector store with metadata"""
        all_documents = []
        all_tables = []
        all_images = []
        
        # Process each file
        for file_path in file_paths:
            print(f"Processing {file_path.name}...")
            
            # Extract text with metadata
            documents = self.document_processor.extract_text_with_metadata(file_path)
            all_documents.extend(documents)
            
            # Extract tables (will fail gracefully if Java not installed)
            tables = self.document_processor.extract_tables(file_path)
            all_tables.extend(tables)
            
            # Extract image information
            images = self.document_processor.extract_images_info(file_path)
            all_images.extend(images)
        
        # Chunk documents
        chunks = self.document_processor.chunk_documents(all_documents)
        
        # Create vector store
        print(f"Creating vector store with {len(chunks)} chunks...")
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)
        
        # Save vector store
        vector_store_path.mkdir(parents=True, exist_ok=True)
        self.vector_store.save_local(str(vector_store_path))
        print(f"Vector store saved to {vector_store_path}")
        
        # Save tables and images metadata
        with open(vector_store_path / "tables.json", "w") as f:
            json.dump(all_tables, f, indent=2)
        
        with open(vector_store_path / "images.json", "w") as f:
            json.dump(all_images, f, indent=2)
        
        # Do not block uploads on a rate-limited external model. Chat can still
        # use the configured model after the collection has been created.
        print("Skipping AI insights during upload; collection is ready for chat.")
        insights = self.insights_generator.local_insights(all_documents[:10])
        
        # Save insights
        with open(vector_store_path / "insights.json", "w") as f:
            json.dump(insights, f, indent=2)
        
        return {
            "status": "success",
            "chunks_created": len(chunks),
            "documents_processed": len(file_paths),
            "tables_extracted": len(all_tables),
            "images_found": len(all_images),
            "insights": insights
        }
    
    def load_vector_store(self, vector_store_path: Path):
        """Load existing vector store and metadata"""
        self.vector_store = FAISS.load_local(
            str(vector_store_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Load tables
        tables_path = vector_store_path / "tables.json"
        if tables_path.exists():
            with open(tables_path, "r") as f:
                self.tables_data = json.load(f)
        
        # Load images
        images_path = vector_store_path / "images.json"
        if images_path.exists():
            with open(images_path, "r") as f:
                self.images_info = json.load(f)
    
    def query_tables(self, question: str) -> Optional[str]:
        """Query tables using LLM"""
        if not self.tables_data:
            return None
        
        # Convert tables to text format
        tables_text = "\n\n".join([
            f"Table from {t['source']}:\n{t['csv_string']}"
            for t in self.tables_data
        ])
        
        prompt = f"""Based on the following tables, answer this question: {question}

Tables:
{tables_text[:3000]}

Answer:"""
        
        return self.llm_manager.generate_response(prompt)
    
    def get_answer_with_sources(
        self, 
        question: str, 
        k: int = 4
    ) -> Dict[str, Any]:
        """Get answer with detailed source information for highlighting"""
        if not self.vector_store:
            return {"error": "Vector store not loaded"}
        
        # Check if question is about tables
        table_keywords = ["table", "data", "row", "column", "value", "sales", "revenue"]
        if any(keyword in question.lower() for keyword in table_keywords):
            table_answer = self.query_tables(question)
            if table_answer:
                if table_answer == AI_UNAVAILABLE:
                    tables_text = "\n\n".join([
                        f"Table from {table['source']}:\n{table['csv_string']}"
                        for table in self.tables_data
                    ])
                    table_answer = "Here are the extracted table details:\n\n" + tables_text[:2000]
                return {
                    "answer": table_answer,
                    "type": "table_query",
                    "sources": []
                }
        
        # Retrieve relevant documents
        docs_and_scores = self.vector_store.similarity_search_with_score(question, k=k)
        
        # Prepare context with source information
        context_parts = []
        sources = []
        
        for doc, score in docs_and_scores:
            context_parts.append(doc.page_content)
            
            # Parse text blocks for highlighting
            text_blocks = []
            if "text_blocks" in doc.metadata:
                try:
                    text_blocks = json.loads(doc.metadata["text_blocks"])
                except:
                    text_blocks = []
            
            sources.append({
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", 0),
                "file_path": doc.metadata.get("file_path", ""),
                "relevance_score": float(score),
                "text_preview": doc.page_content[:200] + "...",
                "text_blocks": text_blocks
            })
        
        context = "\n\n".join(context_parts)
        
        # Generate answer with prompt template
        prompt = f"""Answer the question using only the document context below.
If the context doesn't contain the answer, say so clearly.
Give a complete, well-structured explanation. Include all relevant steps, definitions,
examples, and details found in the context. Use Markdown headings and lists when helpful.

Context from multiple documents:
{context}

Question: {question}

Provide a clear, detailed answer citing specific sources when possible:"""
        
        answer = self.llm_manager.generate_response(prompt)
        if answer == AI_UNAVAILABLE:
            answer = (
                "Here are the most relevant passages from your documents:\n\n"
                + "\n\n".join(f"- {part}" for part in context_parts)
            )
        
        return {
            "answer": answer,
            "type": "document_query",
            "sources": sources,
            "context_used": len(context_parts)
        }


# Main functions to be called from endpoints
def process_files(
    file_paths: List[Path], 
    vector_store_path: Path,
    llm_provider: str = "gemini",
    llm_model: Optional[str] = None
) -> Dict[str, Any]:
    """Main function to process files"""
    rag_system = EnhancedRAGSystem(llm_provider, llm_model)
    return rag_system.process_files(file_paths, vector_store_path)


def get_chat_answer(
    question: str, 
    vector_store_path: Path,
    llm_provider: str = "gemini",
    llm_model: Optional[str] = None
) -> Dict[str, Any]:
    """Main function to get chat answer with sources"""
    rag_system = EnhancedRAGSystem(llm_provider, llm_model)
    rag_system.load_vector_store(vector_store_path)
    return rag_system.get_answer_with_sources(question)


def get_insights(vector_store_path: Path) -> Dict[str, Any]:
    """Get proactive insights for a collection"""
    insights_path = vector_store_path / "insights.json"
    
    if insights_path.exists():
        with open(insights_path, "r") as f:
            return json.load(f)
    
    return {"error": "No insights found"}