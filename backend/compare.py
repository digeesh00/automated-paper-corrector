from typing import Dict, List, Any, Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import google.generativeai as genai
from utils import get_api_key
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class SemanticComparator:
    def __init__(self, method: str = "gemini", model_name: str = "all-MiniLM-L6-v2"):
        self.method = method
        self.model = None
        self.executor = ThreadPoolExecutor(max_workers=3)
        
        if method == "sentence_transformers":
            self.model = SentenceTransformer(model_name)
        elif method == "gemini":
            try:
                api_key = get_api_key("GEMINI_API_KEY")
                if api_key:
                    genai.configure(api_key=api_key)
                    # Using the specified stable model Gemini 2.5 Flash
                    self.gemini_model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Could not initialize Gemini API: {e}")
                self.method = "sentence_transformers"
                self.model = SentenceTransformer(model_name)
                
    def parse_teacher_key_marks(self, master_key_content: str, retry_count: int = 3) -> Dict[str, Dict[str, float]]:
        """
        Parses the master key to strictly identify the exact max marks for every question.
        Returns a dictionary structure: {"Q1": {"marks": 2.0}, "Q2": {"marks": 5.0}}
        """
        prompt = f"""
Goal: Extract the maximum possible marks for EVERY question explicitly listed in the Teacher Key.
Rules:
1. ONLY extract the IDs and the explicit 'Marks' for each question from the provided text.
2. Standardize all Question IDs (e.g., '1.', '1)', 'Q1' should all become 'Q1', 'Q2', etc.).
3. DO NOT guess or infer marks. If marks are missing for a question, ignore it.
4. Output STRICT JSON format.

TEACHER'S MASTER KEY:
{master_key_content}

OUTPUT FORMAT (Strict JSON):
{{
  "Q1": {{"marks": 2.0}},
  "Q2": {{"marks": 5.0}}
}}
"""
        for attempt in range(retry_count):
            try:
                time.sleep(2) # rate limit buffer
                response = self.gemini_model.generate_content(
                    prompt, 
                    generation_config={"temperature": 0.1, "response_mime_type": "application/json"}
                )
                import json
                marks_dict = json.loads(response.text)
                
                # Validation: Ensure it matches the expected structure
                validated_dict = {}
                for k, v in marks_dict.items():
                    if isinstance(v, dict) and "marks" in v:
                        try:
                            validated_dict[str(k).upper().replace(" ", "")] = {"marks": float(v["marks"])}
                        except ValueError:
                            pass
                return validated_dict
            except Exception as e:
                if attempt == retry_count - 1:
                    print(f"Failed to parse teacher marks: {e}")
                    return {}
                time.sleep(5)
    
    def compare_with_gemini(self, teacher_context: str, student_text: str, subject: str, mode: str, threshold: float, teacher_marks_dict: Dict[str, Dict[str, float]], retry_count: int = 3) -> Dict[str, Any]:
        """
        AI-driven comparison with Subject-Aware logic, Global Question Mapping, and Partial Credit support.
        teacher_context: The full consolidated teacher key (Master Key).
        student_text: Fragment of student script (e.g., 2 questions).
        """
        if not teacher_context or not student_text or not str(teacher_context).strip() or not str(student_text).strip():
            return {"similarity": 0.0, "analysis": "Empty content provided for evaluation."}
        
        # Adjust AI temperature based on mode (Low temp for logical accuracy in 'Other' subjects)
        target_temp = 0.7 if mode == "language" else 0.2

        # Dynamic Role Definition based on Sidebar Selection 
        if mode == "language":
            role_instruction = (
                "Role: Strict Language Auditor. Evaluate for grammar, specific vocabulary, "
                "phrasing, creativity, and opinion-based depth. Evaluation must be STRICT."
            )
        else:
            role_instruction = (
                "Role: Logical Meaning Evaluator. IGNORE minor OCR, grammar, or spelling errors. "
                "Focus strictly on finding KEYWORDS and LOGICAL MEANING. If the student "
                "expresses the correct concept using relevant keywords, award marks."
            )

        prompt = f"""
{role_instruction}
Subject Type: {subject}
Task: Evaluate the Student Answer fragment against the provided Master Teacher Key.

TEACHER'S MASTER KEY (Context Base):
{teacher_context}

STUDENT'S ANSWER FRAGMENT (Current Page):
{student_text}

CRITICAL EVALUATION RULES:
1. QUESTION-WISE MAPPING: Identify Question Numbers (e.g., Q1, 1., Part A) in the Student's Answer.
2. GLOBAL KEY SEARCH: Search the entire 'TEACHER'S MASTER KEY' to find the matching question regardless of where it appears in the key.
3. KEYWORD REWARD: Especially for 'Other Subjects', award full or partial marks (0.5 or 1.0) if the student uses correct keywords even if the sentence structure is poor. 
4. LENIENCY: For non-language subjects, do not award 0 marks if the logical meaning is clear and matches the key.
5. THRESHOLD: Use a conceptual match threshold of {threshold}.

OUTPUT FORMAT (Strict JSON):
Ensure the response is valid JSON. Do not use markdown blocks like ```json.
{{
  "total_earned": 2.0,
  "questions": [
    {{
      "id": "Q1",
      "earned": 2.0,
      "feedback": "Explain why marks were given...",
      "confidence": 0.85,
      "confidence_reason": "Good match, but had to rely on synonyms."
    }}
  ]
}}
RULES FOR CALCULATING CONFIDENCE:
- Confidence = 1.00 : Perfect conceptual match, keywords are explicit and clear.
- Confidence = 0.85 : Good match, but you had to rely heavily on synonyms or interpret poor grammar.
- Confidence = 0.70 : Partial completion, logic is slightly confusing or you had to guess the student's intent.
- Confidence = 0.50 : Very ambiguous answer, severe difficulty mapping to the teacher's key.
If confidence <= 0.85, explicitly state which rule triggered this deduction in 'confidence_reason'. Otherwise, return "N/A".
"""
        
        for attempt in range(retry_count):
            try:
                # Essential 12-second delay to stay within Gemini Free Tier limits [cite: 5]
                time.sleep(12) 
                
                response = self.gemini_model.generate_content(
                    prompt, 
                    generation_config={"temperature": target_temp, "response_mime_type": "application/json"}
                )
                resp_text = response.text
                
                import json
                try:
                    parsed = json.loads(resp_text)
                    earned = float(parsed.get("total_earned", 0.0))
                    
                    # STRICT MAX MARKS ENFORCEMENT
                    questions = parsed.get("questions", [])
                    total_strict = 0.0
                    for q in questions:
                        # Ensure ID format matches the dict (e.g. Q1, Q2)
                        q_id = str(q.get("id", "Q")).upper().replace(" ", "")
                        if not q_id.startswith("Q"):
                            q_id = f"Q{q_id}" 
                            
                        # Use teacher key directly
                        strict_possible = teacher_marks_dict.get(q_id, {"marks": 0.0})["marks"]
                        q["possible"] = strict_possible
                        
                        # Cap the earned marks to not exceed max marks (anti-hallucination)
                        if q.get("earned", 0) > strict_possible:
                            q["earned"] = strict_possible
                            
                        total_strict += strict_possible
                        
                    total = total_strict if total_strict > 0 else 1.0
                    
                    # Fallback string analysis
                    analysis = " | ".join([f"{q.get('id', 'Q')}: {q.get('earned')}/{q.get('possible')} - {q.get('feedback')}" for q in questions])
                except json.JSONDecodeError:
                    earned = 0.0
                    total = 1.0
                    analysis = resp_text
                    questions = []

                ratio = max(0.0, min(1.0, earned / total)) if total > 0 else 0.0
                return {
                    "similarity": ratio, 
                    "analysis": analysis if analysis else resp_text,
                    "earned": earned,
                    "total": total,
                    "questions": questions
                }
                
            except Exception as e:
                if "429" in str(e):
                    # Extended back-off if hit by rate limit
                    time.sleep(20)
                if attempt == retry_count - 1:
                    return {"similarity": 0.0, "analysis": f"Error: {str(e)}"}
                time.sleep(5)

    async def compare_page_async(self, master_key_content: str, student_page: Dict, subject: str, mode: str, threshold: float, teacher_marks_dict: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Orchestrates the comparison using the full Master Key context."""
        loop = asyncio.get_event_loop()
        s_content = student_page.get("content") or ""
        
        result = await loop.run_in_executor(
            self.executor, self.compare_with_gemini, master_key_content, s_content, subject, mode, threshold, teacher_marks_dict
        )
        result["student_page_no"] = student_page.get("page_no", 0)
        # Pass extraction confidence to the evaluator for display in app.py 
        result["extraction_confidence"] = student_page.get("extraction_confidence", 0.0)
        result["extraction_reason"] = student_page.get("extraction_reason", "N/A")
        return result
    
    async def compare_documents(self, teacher_data: Dict, student_data: Dict, subject: str = "Other Subjects", mode: str = "technical", threshold: float = 0.50, master_key_content: str = "", teacher_marks_dict: Dict[str, Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Processes all student pages against the Global Master Key context."""
        student_pages = student_data.get("pages", [])
        if teacher_marks_dict is None:
            teacher_marks_dict = {}
            
        tasks = []
        for i in range(len(student_pages)):
            tasks.append(self.compare_page_async(master_key_content, student_pages[i], subject, mode, threshold, teacher_marks_dict))
        
        return await asyncio.gather(*tasks)

    def __del__(self):
        """Cleanup thread pool executor."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)