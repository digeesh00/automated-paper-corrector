"""
Pipeline orchestrator that connects all modules into a seamless workflow.
Coordinates extraction, comparison, evaluation, and feedback generation.
Updated with Leniency Logic (0.55 threshold) and Global Context Mapping.
"""
import asyncio
import time
import re
from typing import Dict, Any, Optional, List
from pathlib import Path


# Module imports
from extraction import DocumentExtractor, extract_documents
from compare import SemanticComparator
from evaluation import Evaluator
from feedback import FeedbackGenerator
from utils import save_json, ensure_directory_exists, check_api_prerequisites


class CorrectionPipeline:
    """Orchestrates the complete paper correction workflow."""
    
    def __init__(
        self,
        comparison_method: str = "gemini",
        use_ai_feedback: bool = False,
        total_marks: float = 100.0,
        output_dir: str = "results"
    ):
        """Initialize core components of the correction pipeline."""
        self.comparison_method = comparison_method
        self.use_ai_feedback = use_ai_feedback
        self.total_marks = total_marks
        self.output_dir = output_dir
        
        self.extractor = DocumentExtractor()
        self.comparator = SemanticComparator(method=comparison_method)
        self.evaluator = Evaluator(total_marks=total_marks)
        self.feedback_generator = FeedbackGenerator(use_ai=use_ai_feedback)
        
        ensure_directory_exists(output_dir)
    
    async def extract_phase(self, teacher_file_path: str, student_file_path: str, reference_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Phase 1: Extract text and parse metadata (Name and Roll No)."""
        extracted_data = await extract_documents(teacher_file_path, student_file_path, reference_file_path)
        
        if 'student_script' not in extracted_data:
            raise KeyError("Critical Error: 'student_script' missing from extraction results.")

        student_script = extracted_data['student_script']
        
        # Pull metadata directly from the extraction module's findings
        extracted_data['student_name'] = student_script.get('student_name', 'Unknown')
        extracted_data['roll_no'] = student_script.get('roll_no', 'Unknown')

        # FIX: Ensure content is cleaned and confidence is preserved for each page
        for page in student_script.get('pages', []):
            raw = page.get('raw_text', '')
            if "CONTENT:" in raw:
                # Update content to exclude the metadata headers for cleaner comparison
                page['content'] = raw.split("CONTENT:")[1].strip()
            
            # Ensure extraction_confidence exists (defaults to 0.85 if missing)
            if 'extraction_confidence' not in page:
                page['extraction_confidence'] = 0.85
        # Save the raw extracted text into a JSON file as per user request
        extraction_output_path = Path("results") / "extracted_text.json"
        save_json(extracted_data, str(extraction_output_path))
        print(f"💾 Saved extracted text to {extraction_output_path}")
        
        return extracted_data

    async def run_async(self, t_path: str, s_path: str, r_path: Optional[str] = None, save_results: bool = True, subject: str = "General") -> Dict[str, Any]:
        """Main execution flow with Dynamic Marks Detection and Global Mapping."""
        pipeline_start = time.time()
        
        # Phase 1: Extraction
        extracted_data = await self.extract_phase(t_path, s_path, r_path)
        
        # --- DYNAMIC TOTAL MARKS DETECTION ---
        # We check the teacher's first page for "METADATA_MAX_MARKS" provided by extraction.py
        teacher_key = extracted_data.get('teacher_key', {})
        teacher_pages = teacher_key.get('pages', [])
        
        if not teacher_pages:
             raise ValueError("Teacher key extraction failed. No pages found. Check the file or Gemini API key.")
             
        teacher_raw = teacher_pages[0].get('raw_text', '')
        max_marks_match = re.search(r"METADATA_MAX_MARKS:\s*([\d.]+)", teacher_raw)
        
        if max_marks_match:
            detected_max = float(max_marks_match.group(1))
            self.total_marks = detected_max
            # Re-initialize or update the evaluator with the correct total
            self.evaluator.total_marks = detected_max
            print(f"🎯 Dynamic Mapping: Set Total Marks to {detected_max}")

        # --- DUAL-MODE LOGIC ---
        if subject == "Language":
            eval_mode = "language"
            threshold = 0.85 
        else:
            eval_mode = "technical"
            threshold = 0.50 

        # --- GLOBAL CONTEXT MAPPING ---
        full_teacher_key = "\n\n".join([p.get("content", "") for p in extracted_data['teacher_key']['pages']])
        
        # --- STRICT MAX MARKS DICTIONARY ---
        print("🎯 Extracting Strict Max Marks Dictionary from Teacher Key...")
        teacher_marks_dict = self.comparator.parse_teacher_key_marks(full_teacher_key)
        print(f"📋 Teacher Max Marks Dict: {teacher_marks_dict}")
        
        # Phase 2: Comparison
        comparison_results = await self.comparator.compare_documents(
            teacher_data=extracted_data['teacher_key'], 
            student_data=extracted_data['student_script'], 
            subject=subject,
            mode=eval_mode,
            threshold=threshold,
            master_key_content=full_teacher_key,
            teacher_marks_dict=teacher_marks_dict
        )
        
        # Evaluation module naturally groups the structured sums returned strictly from the dict
        evaluation_report = self.evaluator.generate_evaluation_report(
            comparison_results=comparison_results,
            teacher_marks_dict=teacher_marks_dict,
            teacher_file=extracted_data['teacher_key'].get('file_name'),
            student_file=extracted_data['student_script'].get('file_name'),
            student_info={
                "name": extracted_data.get('student_name'),
                "roll_no": extracted_data.get('roll_no')
            }
        )
        
        # ... rest of the code (Feedback and Save) remains same ...
        
        # Phase 4: Feedback
        feedback = self.feedback_generator.generate_complete_feedback(
            evaluation=evaluation_report['evaluation'],
            teacher_data=extracted_data['teacher_key'],
            student_data=extracted_data['student_script']
        )
        
        final_results = {
            "extracted_data": extracted_data,
            "evaluation_report": evaluation_report,
            "feedback": feedback,
            "pipeline_metadata": {
                "subject": subject,
                "eval_mode": eval_mode,
                "elapsed_time": time.time() - pipeline_start
            }
        }
        
        if save_results:
            self._save_results(final_results, s_path)
        
        return final_results

    def run_sync(self, t_path: str, s_path: str, r_path: Optional[str] = None, save_results: bool = True, subject: str = "General"):
        """Synchronous wrapper for run_async."""
        return asyncio.run(self.run_async(t_path, s_path, r_path, save_results, subject))

   # Inside pipeline.py

    def _save_results(self, results: Dict[str, Any], s_path: str):
        """Saves report using a sanitized student name and roll number."""
        # Extract raw metadata
        raw_name = results['extracted_data'].get('student_name', 'Unknown')
        raw_roll = results['extracted_data'].get('roll_no', 'Unknown')
        
        # FIX: Sanitize the filename to remove newlines, colons, and extra spaces
        def sanitize(text):
            # Remove newlines, colons, and any other illegal characters
            text = text.replace('\n', '').replace('\r', '').replace(':', '_')
            # Only allow alphanumeric, underscores, and hyphens
            return re.sub(r'[^\w\-_\. ]', '', text).strip()

        name = sanitize(raw_name)
        roll = sanitize(raw_roll)
        
        # Construct a clean filename
        filename = f"{name}_{roll}_report.json".replace(" ", "_")
        
        save_json(results['evaluation_report'], str(Path(self.output_dir) / filename))


def run_correction_pipeline(teacher_file_path: str, student_file_path: str, reference_file_path: Optional[str] = None, total_marks: float = 100.0, subject: str = "General"):
    """Global entry point."""
    pipeline = CorrectionPipeline(total_marks=total_marks)
    return pipeline.run_sync(teacher_file_path, student_file_path, reference_file_path, subject=subject)