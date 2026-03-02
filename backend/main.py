import shutil
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pipeline import CorrectionPipeline

app = FastAPI(title="Automated Paper Correction API")

# Configure CORS for the frontend Vite application (typically runs on 5173 or localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development. In production restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def save_upload_file_tmp(upload_file: UploadFile) -> str:
    """Saves a FastAPI UploadFile to a temporary file, returning the path."""
    try:
        suffix = os.path.splitext(upload_file.filename)[1] if upload_file.filename else ".tmp"
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, 'wb') as f:
            shutil.copyfileobj(upload_file.file, f)
        return path
    finally:
        upload_file.file.close()

@app.post("/api/evaluate")
async def evaluate_papers(
    teacherKey: UploadFile = File(...),
    studentScript: UploadFile = File(...),
    subject: str = Form("Language")
):
    if not teacherKey.filename or not studentScript.filename:
        raise HTTPException(status_code=400, detail="Both teacher key and student script are required")
        
    t_path = save_upload_file_tmp(teacherKey)
    s_path = save_upload_file_tmp(studentScript)
    
    try:
        # Run the existing pipeline logic asynchronously
        pipeline = CorrectionPipeline(total_marks=100.0)
        results = await pipeline.run_async(
            t_path=t_path,
            s_path=s_path,
            subject=subject
        )
        
        if not results or 'evaluation_report' not in results:
             raise HTTPException(status_code=500, detail="Pipeline failed to return valid results.")
             
        eval_data = results['evaluation_report'].get('evaluation', {})
        
        # Calculate accuracy across logic/extraction confidence if any
        page_scores = eval_data.get('page_scores', [])
        if page_scores:
            avg_accuracy = sum(p.get('extraction_confidence', 0) for p in page_scores) / len(page_scores)
        else:
            avg_accuracy = 0.0
            
        # Parse questions from all pages into a flat array, mapping to expected frontend shape
        frontend_questions = []
        for p in page_scores:
            for q in p.get('questions', []):
                 frontend_questions.append({
                     "id": q.get('id', 'N/A'),
                     "score": q.get('score', 0),
                     "maxScore": q.get('max_score', 0),
                     "feedback": q.get('feedback', '')
                 })
                 
        detailed_feedback = results.get("feedback", "No detailed feedback provided by the pipeline.")
                 
        # Construct the response object that matches the App.tsx Result type
        frontend_response = {
            "totalScore": eval_data.get("total_score", 0),
            "maxScore": eval_data.get("max_score", 100),
            "accuracy": round(avg_accuracy * 100, 2),
            "grade": eval_data.get("grade", "N/A"),
            "status": str(eval_data.get("status", "FAIL")).upper(),
            "questionBreakdown": frontend_questions,
            "improvementTips": [
                "Review the feedback to understand missed points.",
                "Ensure logical meaning matches the teacher's key."
            ], # Static tips for now unless pipeline is updated to return them natively
            "detailedFeedback": detailed_feedback,
            "overallReport": f"Final Grade: {eval_data.get('grade', 'N/A')} | Status: {eval_data.get('status', 'FAIL')}"
        }
        
        return frontend_response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error evaluating: {str(e)}")
    finally:
        # Cleanup temp files
        if os.path.exists(t_path): os.remove(t_path)
        if os.path.exists(s_path): os.remove(s_path)

if __name__ == "__main__":
    import uvicorn
    # Local application runner
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
