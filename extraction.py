"""
Text extraction module optimized for Question-Centric Mapping.
Includes Technical Glossary to fix spelling errors and Confidence Scoring.
"""
import asyncio
import os
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
from PIL import Image
import google.generativeai as genai
from pdf2image import convert_from_path
import time

class DocumentExtractor:
    """Handles text extraction from PDF or Images using Gemini 2.5 Flash."""
    
    def __init__(self):
        """Initialize the document extractor with Gemini."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.rate_limit_lock = asyncio.Semaphore(1)
    
    async def transcribe_page(self, image: Image.Image, page_no: int) -> Dict[str, Any]:
        """Transcribes a single page with Technical Glossary and Confidence scoring."""
        async with self.rate_limit_lock:
            try:
                header_instruction = ""
                if page_no == 1:
                    header_instruction = (
                        "First, look at the top right corner of the page. "
                        "Identify the Student Name and Roll Number written there. "
                        "Format them as METADATA_NAME: [Name] and METADATA_ROLL: [Roll No]. "
                        "Identify the 'MAX MARKS' or 'TOTAL MARKS' listed in the header. Format as METADATA_MAX_MARKS: [Number]."
                    )
                
                glossary = (
                    "TECHNICAL GLOSSARY: Inductive, Gradient, Divergence, Activation, "
                    "Penetration, NetBIOS, Vulnerability, Supervised, Reinforcement, MSE. "
                    "Use this glossary to correct minor OCR/handwriting misspellings."
                )

                prompt = (
                    f"{header_instruction}\n"
                    f"{glossary}\n"
                    "Transcribe the text from this exam paper exactly. "
                    "IMPORTANT: Identify all Question Numbers (e.g., Q1, Q2, Part A) on their own line. "
                    "Include an EXTRACTION_CONFIDENCE score between 0 and 1 based on handwriting legibility. "
                    "Return the output in this strict format:\n"
                    "METADATA_NAME: [Name or 'Unknown']\n"
                    "METADATA_ROLL: [Roll No or 'Unknown']\n"
                    "EXTRACTION_CONFIDENCE: [Numeric Score]\n"
                    "CONTENT: [The full transcribed text]"
                )
                
                await asyncio.sleep(5) 
                response = await self.model.generate_content_async([prompt, image])
                raw_text = response.text if response.text else ""

                # Robust Parsing with Regex
                student_name = "Unknown"
                roll_no = "Unknown"
                confidence = 0.0
                
                # Extract Name
                name_match = re.search(r"METADATA_NAME:\s*(.*)", raw_text)
                if name_match:
                    student_name = name_match.group(1).split("\n")[0].strip()

                # Extract Roll
                roll_match = re.search(r"METADATA_ROLL:\s*(.*)", raw_text)
                if roll_match:
                    roll_no = roll_match.group(1).split("\n")[0].strip()

                # FIX: Improved Confidence Extraction
                conf_match = re.search(r"EXTRACTION_CONFIDENCE:\s*([\d.]+)", raw_text)
                if conf_match:
                    try:
                        confidence = float(conf_match.group(1))
                    except ValueError:
                        confidence = 0.5  # Fallback
                
                # Extract Content
                content_part = raw_text
                if "CONTENT:" in raw_text:
                    content_part = raw_text.split("CONTENT:")[1].strip()

                return {
                    "page_no": page_no, 
                    "content": content_part, 
                    "student_name": student_name,
                    "roll_no": roll_no,
                    "extraction_confidence": confidence,
                    "raw_text": raw_text 
                }
            except Exception as e:
                print(f"❌ Error on page {page_no}: {str(e)}")
                return {
                    "page_no": page_no, "content": "", 
                    "student_name": "Unknown", "roll_no": "Unknown",
                    "extraction_confidence": 0.0
                }
        
    async def extract_from_file(self, file_path: str, source: str) -> Dict[str, Any]:
        """Extract text from a file sequentially."""
        try:
            print(f"📑 Extracting {source} from: {Path(file_path).name}")
            file_ext = Path(file_path).suffix.lower()
            images = convert_from_path(file_path, dpi=200) if file_ext == '.pdf' else [Image.open(file_path)]
            
            pages_content = []
            for i, img in enumerate(images):
                result = await self.transcribe_page(img, i + 1)
                pages_content.append(result)
            
            return {
                "source": source,
                "total_pages": len(pages_content),
                "pages": pages_content,
                "file_name": Path(file_path).name,
                "student_name": pages_content[0].get("student_name", "Unknown") if pages_content else "Unknown",
                "roll_no": pages_content[0].get("roll_no", "Unknown") if pages_content else "Unknown"
            }
        except Exception as e:
            print(f"❌ Extraction Error: {str(e)}")
            return {"source": source, "pages": [], "error": str(e)}

async def extract_documents(teacher_path: str, student_path: str, reference_path: Optional[str] = None) -> Dict[str, Any]:
    extractor = DocumentExtractor()
    teacher_data = await extractor.extract_from_file(teacher_path, "teacher")
    student_data = await extractor.extract_from_file(student_path, "student")
    return {
        "teacher_key": teacher_data, "student_script": student_data,
        "extraction_status": "completed"
    }