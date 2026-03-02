export interface EvaluationResult {
  totalScore: number;
  maxScore: number;
  accuracy: number;
  grade: string;
  status: 'PASS' | 'FAIL';
  questionBreakdown: {
    id: string;
    score: number;
    maxScore: number;
    feedback: string;
  }[];
  improvementTips: string[];
  detailedFeedback: string;
  overallReport: string;
}

export interface FileData {
  name: string;
  content: string; // base64 or text
  type: string;
  originalFile: File;
}
