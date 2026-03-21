"""
Text extraction module optimized for Question-Centric Mapping.
Upgraded to Qwen3.5-9B with Parallel Async Processing and 3-argument support.
"""
import asyncio
import os
import re
import base64
import io
import httpx
from typing import Dict, List, Any, Optional
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path

class DocumentExtractor:
    """Handles text extraction from PDF or Images using Qwen 3.5 via OpenRouter."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model_name = 'qwen/qwen3.5-9b'
        
        # Limit to 5 concurrent pages to avoid rate limits
        self.rate_limit_lock = asyncio.Semaphore(5)

    async def transcribe_page(self, client: httpx.AsyncClient, image: Image.Image, page_no: int) -> Dict[str, Any]:
        """Transcribes a single page with Technical Glossary and Speed optimizations."""
        async with self.rate_limit_lock:
            retry_count = 3
            for attempt in range(retry_count):
                try:
                    # Adaptive resizing to keep payloads small/fast
                    if image.width > 2000:
                        image.thumbnail((2000, 2000))

                    header_instruction = ""
                    if page_no == 1:
                        header_instruction = (
                            "First, look at the top right corner. "
                            "Identify the Student Name and Roll Number. "
                            "Format: METADATA_NAME: [Name], METADATA_ROLL: [Roll No]. "
                        )
                    
                    glossary = (
                        "TECHNICAL GLOSSARY: Inductive, Gradient, Divergence, Activation, "
                        "Penetration, NetBIOS, Vulnerability, Supervised, Reinforcement, MSE."
                    )

                    prompt = (
                        f"{header_instruction}\n"
                        f"{glossary}\n"
                        "Transcribe the text from this exam paper exactly. "
                        "Identify all Question Numbers (e.g., Q1, Q2) on their own line.\n"
                        "RULES FOR CALCULATING EXTRACTION_CONFIDENCE:\n"
                        "- Start with a baseline of 1.0.\n"
                        "- Deduct 0.15 for every word or phrase that is completely unreadable or heavily blurred.\n"
                        "- Deduct 0.10 if the page appears slightly cut off at the edges but is mostly readable.\n"
                        "- If the text is perfectly clear and legible, return 1.0.\n"
                        "- Lowest possible score is 0.1.\n"
                        "Return format exactly as follows:\n"
                        "METADATA_NAME: [Name]\n"
                        "METADATA_ROLL: [Roll No]\n"
                        "EXTRACTION_CONFIDENCE: [Score 0.1-1.0]\n"
                        "EXTRACTION_REASON: [Brief 1 sentence reason for the score]\n"
                        "CONTENT: [Full Transcription]"
                    )
                    
                    buffered = io.BytesIO()
                    if image.mode in ('RGBA', 'P'):
                        image = image.convert('RGB')
                    image.save(buffered, format="JPEG", quality=80)
                    img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

                    payload = {
                        "model": self.model_name,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                            ]
                        }],
                        "temperature": 0.1,
                        "include_reasoning": False, # Disable thinking for speed
                        "reasoning": {"effort": "none"}
                    }

                    headers = {
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": "http://localhost:8000",
                        "X-Title": "Paper Corrector",
                        "Content-Type": "application/json"
                    }

                    response = await client.post(self.url, headers=headers, json=payload, timeout=120.0)
                    response.raise_for_status()
                    res_json = response.json()
                    
                    raw_text = res_json["choices"][0]["message"].get("content", "")

                    # --- Robust Parsing ---
                    name_match = re.search(r"METADATA_NAME:\s*(.*)", raw_text)
                    roll_match = re.search(r"METADATA_ROLL:\s*(.*)", raw_text)
                    conf_match = re.search(r"EXTRACTION_CONFIDENCE:\s*([\d.]+)", raw_text)
                    reason_match = re.search(r"EXTRACTION_REASON:\s*(.*)", raw_text)
                    
                    return {
                        "page_no": page_no, 
                        "content": raw_text.split("CONTENT:")[1].strip() if "CONTENT:" in raw_text else raw_text, 
                        "student_name": name_match.group(1).strip() if name_match else "Unknown",
                        "roll_no": roll_match.group(1).strip() if roll_match else "Unknown",
                        "extraction_confidence": float(conf_match.group(1)) if conf_match else 0.85,
                        "extraction_reason": reason_match.group(1).strip() if reason_match else "N/A",
                        "raw_text": raw_text 
                    }

                except Exception as e:
                    if attempt < retry_count - 1:
                        await asyncio.sleep(5 * (attempt + 1))
                        continue
                    return {"page_no": page_no, "content": f"ERROR: {str(e)}", "student_name": "Unknown"}

    async def extract_from_file(self, client: httpx.AsyncClient, file_path: str, source: str) -> Dict[str, Any]:
        """Parallel async extraction for PDF/Image files."""
        try:
            print(f"📑 Extracting {source}: {Path(file_path).name}")
            file_ext = Path(file_path).suffix.lower()
            
            # 130 DPI is the sweet spot for Qwen3.5 vision accuracy vs speed
            images = convert_from_path(file_path, dpi=130) if file_ext == '.pdf' else [Image.open(file_path)]
            
            tasks = [self.transcribe_page(client, img, i + 1) for i, img in enumerate(images)]
            pages_content = await asyncio.gather(*tasks)
            pages_content.sort(key=lambda x: x['page_no'])
            
            return {
                "source": source,
                "total_pages": len(pages_content),
                "pages": pages_content,
                "file_name": Path(file_path).name,
                "student_name": pages_content[0].get("student_name", "Unknown"),
                "roll_no": pages_content[0].get("roll_no", "Unknown")
            }
        except Exception as e:
            return {"source": source, "pages": [], "error": str(e)}

async def extract_documents(teacher_path: str, student_path: str, reference_path: Optional[str] = None) -> Dict[str, Any]:
    """Entry point compatible with your 3-argument pipeline call."""
    extractor = DocumentExtractor()
    async with httpx.AsyncClient() as client:
        # Create core tasks
        tasks = [
            extractor.extract_from_file(client, teacher_path, "teacher"),
            extractor.extract_from_file(client, student_path, "student")
        ]
        
        # Add optional reference task if provided by pipeline.py
        if reference_path:
            tasks.append(extractor.extract_from_file(client, reference_path, "reference"))
            
        results = await asyncio.gather(*tasks)
    
    output = {
        "teacher_key": results[0],
        "student_script": results[1],
        "extraction_status": "completed"
    }
    
    if len(results) > 2:
        output["reference_material"] = results[2]
        
    return output