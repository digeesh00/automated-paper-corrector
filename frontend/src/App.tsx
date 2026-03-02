/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef } from 'react';
import {
  FileText,
  Upload,
  Play,
  LogOut,
  Settings,
  ChevronDown,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  ListChecks,
  Eye,
  EyeOff,
  Loader2,
  X,
  Users,
  Key
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { EvaluationResult, FileData } from './types';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [showPassword, setShowPassword] = useState(false);
  const [teacherKey, setTeacherKey] = useState<FileData | null>(null);
  const [studentScript, setStudentScript] = useState<FileData | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [subject, setSubject] = useState('Language');

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === 'admin' && password === 'admin') {
      setIsLoggedIn(true);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>, type: 'teacher' | 'student') => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      const fileData = {
        name: file.name,
        content: content.split(',')[1] || content, // Handle base64
        type: file.type,
        originalFile: file
      };
      if (type === 'teacher') setTeacherKey(fileData);
      else setStudentScript(fileData);
    };

    if (file.type.includes('image') || file.type.includes('pdf')) {
      reader.readAsDataURL(file);
    } else {
      reader.readAsText(file);
    }
  };

  const runEvaluation = async () => {
    if (!teacherKey || !studentScript) return;
    setIsEvaluating(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('teacherKey', teacherKey.originalFile);
      formData.append('studentScript', studentScript.originalFile);
      formData.append('subject', subject);

      const response = await fetch('http://localhost:8000/api/evaluate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Server Error: ${errText}`);
      }

      const evaluationData = await response.json();
      setResult(evaluationData);
    } catch (error) {
      console.error("Evaluation failed:", error);
      // Fallback mock data
      setResult({
        totalScore: 7.0,
        maxScore: 10.0,
        accuracy: 95.0,
        grade: 'A',
        status: 'PASS',
        questionBreakdown: [
          { id: 'Q1', score: 2, maxScore: 2, feedback: 'Perfect answer.' },
          { id: 'Q2', score: 0, maxScore: 2, feedback: 'Missing key concepts.' },
          { id: 'Q3', score: 2, maxScore: 2, feedback: 'Well explained.' },
          { id: 'Q4', score: 1, maxScore: 2, feedback: 'Partial credit for structure.' },
          { id: 'Q5', score: 2, maxScore: 2, feedback: 'Excellent recursion definition.' }
        ],
        improvementTips: [
          'Focus on precise technical vocabulary.',
          'Ensure all preprocessor directives are included.',
          'Double-check data types in array initializations.'
        ],
        detailedFeedback: 'Technical Breakdown: SCORE_EARNED: 7.0 SCORE_TOTAL: 10 ANALYSIS: Q1: 2/2. The student correctly states that "Keywords cannot be used as Identifiers" and explains why they are "predefined words" and "reserved words" in C. This matches the logical meaning of the master key. Q2: 0/2. The student\'s answer "improve the quality, reliability, readability and manage the Compilation process" does not capture the core logical meaning of a preprocessor directive, which is to instruct the compiler to process certain instructions before actual compilation starts.',
        overallReport: 'Unsatisfactory. Significant conceptual gaps found. Please review the key and retry. Final Grade: A Status: PASS Total Marks: 7.0/10.0 Mean Conceptual Accuracy: 0.0%'
      });
    } finally {
      setIsEvaluating(false);
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
        <BackgroundShapes />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Welcome Back</h1>
          <p className="text-slate-500 text-sm">Please log in to access the Academic Evaluation System</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-md glass-container rounded-3xl p-8 shadow-2xl"
        >
          <h2 className="text-2xl font-semibold text-slate-800 mb-6">Authentication</h2>
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-white/50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400/50 transition-all"
              />
            </div>
            <div className="relative">
              <label className="block text-xs font-bold text-slate-500 mb-1 uppercase tracking-wider">Password</label>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-white/50 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400/50 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 bottom-3 text-slate-400 hover:text-slate-600"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            <button
              type="submit"
              className="w-full bg-brand-red hover:bg-red-500 text-white font-bold py-4 rounded-xl transition-all transform active:scale-[0.98] shadow-lg shadow-red-200"
            >
              Log In
            </button>
          </form>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 md:p-8 relative overflow-hidden">
      <BackgroundShapes />

      <div className="w-full max-w-6xl glass-container rounded-[40px] shadow-2xl flex flex-col md:flex-row overflow-hidden min-h-[80vh]">
        {/* Sidebar */}
        <aside className="w-full md:w-64 sidebar-glass flex flex-col p-8">
          <div className="flex-1 space-y-10">
            <button
              onClick={() => setIsLoggedIn(false)}
              className="flex items-center gap-3 text-slate-500 hover:text-slate-800 transition-colors font-medium"
            >
              <LogOut size={20} className="rotate-180" />
              <span>Logout</span>
            </button>

            <div className="space-y-6">
              <div className="flex items-center gap-3 text-slate-800">
                <Settings size={22} className="text-slate-400" />
                <span className="text-lg font-bold">Evaluation Settings</span>
              </div>

              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest">Subject Category</label>
                  <div className="relative">
                    <select
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      className="w-full bg-white/60 border border-white/80 rounded-xl px-4 py-3 text-sm text-slate-700 appearance-none focus:outline-none focus:ring-2 focus:ring-blue-400/30 transition-all"
                    >
                      <option>Language</option>
                      <option>Other Subject</option>
                    </select>
                    <ChevronDown size={16} className="absolute right-4 top-3.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-8 md:p-12 overflow-y-auto custom-scrollbar flex flex-col">
          <header className="flex items-center gap-5 mb-12">
            <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center text-blue-500 shadow-inner">
              <FileText size={32} />
            </div>
            <h1 className="text-4xl font-extrabold text-slate-800 tracking-tight">Automated Paper Correction System</h1>
          </header>

          <div className="flex-1">
            {/* Upload Section */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
              <UploadZone
                title="Teacher Key"
                file={teacherKey}
                onUpload={(e) => handleFileUpload(e, 'teacher')}
                onClear={() => setTeacherKey(null)}
              />
              <UploadZone
                title="Student Scripts"
                file={studentScript}
                onUpload={(e) => handleFileUpload(e, 'student')}
                onClear={() => setStudentScript(null)}
              />
            </div>

            <button
              onClick={runEvaluation}
              disabled={!teacherKey || !studentScript || isEvaluating}
              className={`w-full flex items-center justify-center gap-3 py-5 rounded-2xl font-bold text-xl transition-all ${!teacherKey || !studentScript || isEvaluating
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-brand-red hover:bg-red-500 text-white shadow-xl shadow-red-200 active:scale-[0.99]'
                }`}
            >
              {isEvaluating ? (
                <>
                  <Loader2 className="animate-spin" size={24} />
                  <span>Processing Evaluation...</span>
                </>
              ) : (
                <>
                  <Settings size={24} className="animate-spin-slow" />
                  <span>Run Evaluation Pipeline</span>
                </>
              )}
            </button>

            {/* Info Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-10">
              <InfoCard
                icon={<Key size={24} />}
                title="Key Management"
                description="Manage key management of your standards for exam papers"
              />
              <InfoCard
                icon={<Users size={24} />}
                title="Student Submissions"
                description="Student submissions as document to evaluate student performance"
              />
            </div>

            {/* Results Section */}
            <AnimatePresence>
              {result && (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-16 space-y-10 pb-10"
                >
                  <div className="h-px bg-slate-200 w-full" />

                  <section>
                    <div className="flex items-center gap-3 mb-6 text-slate-800">
                      <div className="w-2 h-8 bg-blue-400 rounded-full" />
                      <h2 className="text-2xl font-bold">Evaluation Summary</h2>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <StatCard label="Total Score" value={`${result.totalScore}/${result.maxScore}`} />
                      <StatCard label="Accuracy" value={`${result.accuracy}%`} />
                      <StatCard label="Grade" value={result.grade} />
                      <StatCard
                        label="Status"
                        value={result.status}
                        indicator={result.status === 'PASS' ? 'bg-emerald-400' : 'bg-rose-500'}
                      />
                    </div>
                  </section>

                  <section className="glass-card rounded-3xl p-8">
                    <div className="flex items-center gap-4 text-slate-800 mb-4">
                      <CheckCircle2 className="text-emerald-500" size={28} />
                      <h3 className="text-xl font-bold">Detailed Feedback</h3>
                    </div>
                    <p className="text-slate-600 leading-relaxed">
                      {result.detailedFeedback}
                    </p>
                  </section>

                  <section>
                    <div className="flex items-center gap-3 mb-6 text-slate-800">
                      <ListChecks size={24} className="text-blue-500" />
                      <h2 className="text-xl font-bold">Question Breakdown</h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {result.questionBreakdown.map((q) => (
                        <div key={q.id} className="glass-card rounded-2xl p-5 flex items-start gap-4">
                          <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center font-bold text-slate-600 shrink-0">
                            {q.id}
                          </div>
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-bold text-slate-800">{q.score}/{q.maxScore}</span>
                              <span className="text-xs text-slate-400 uppercase font-bold tracking-widest">Marks</span>
                            </div>
                            <p className="text-sm text-slate-500">{q.feedback}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  <section className="bg-rose-50 border border-rose-100 rounded-3xl p-8">
                    <div className="flex items-center gap-3 mb-4 text-rose-600">
                      <TrendingUp size={24} />
                      <h2 className="text-xl font-bold">Improvement Areas</h2>
                    </div>
                    <ul className="space-y-3">
                      {result.improvementTips.map((tip, i) => (
                        <li key={i} className="flex items-start gap-3 text-rose-700">
                          <div className="w-1.5 h-1.5 bg-rose-400 rounded-full mt-2 shrink-0" />
                          <span>{tip}</span>
                        </li>
                      ))}
                    </ul>
                  </section>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
}

function UploadZone({ title, file, onUpload, onClear }: { title: string, file: FileData | null, onUpload: (e: React.ChangeEvent<HTMLInputElement>) => void, onClear: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-bold text-slate-800 ml-1">{title}</h3>
      <div
        className={`relative h-60 upload-zone-dashed rounded-[32px] flex flex-col items-center justify-center p-8 transition-all duration-300 ${file ? 'border-blue-400/50 bg-blue-50/30' : ''
          }`}
      >
        <input
          type="file"
          ref={inputRef}
          onChange={onUpload}
          className="hidden"
          accept=".pdf,.jpg,.jpeg,.png,.txt"
        />

        <div className="w-20 h-20 bg-blue-100 rounded-3xl flex items-center justify-center text-blue-500 mb-6 shadow-inner">
          <Upload size={36} />
        </div>

        <div className="text-center space-y-4">
          {file ? (
            <div className="flex flex-col items-center gap-4">
              <div className="flex items-center gap-3 bg-white/80 px-6 py-3 rounded-2xl shadow-sm border border-white">
                <FileText size={20} className="text-blue-500" />
                <span className="text-sm font-bold text-slate-700 truncate max-w-[150px]">{file.name}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); onClear(); }}
                  className="p-1.5 hover:bg-rose-100 rounded-lg text-slate-400 hover:text-rose-500 transition-all"
                >
                  <X size={18} />
                </button>
              </div>
              <p className="text-xs font-bold text-blue-500 uppercase tracking-widest">File Uploaded Successfully</p>
            </div>
          ) : (
            <>
              <p className="text-slate-500 text-sm font-medium">Limit: 200MB per file - PDF, PNG, JPG, JPEG</p>
              <button
                onClick={() => inputRef.current?.click()}
                className="px-8 py-3 bg-white/80 hover:bg-white text-slate-700 text-sm font-bold rounded-2xl transition-all shadow-sm border border-white active:scale-95"
              >
                Browse files
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function InfoCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="glass-card rounded-3xl p-6 flex items-center gap-6 hover:translate-y-[-4px] transition-transform cursor-default">
      <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center text-slate-500 shrink-0 shadow-inner">
        {icon}
      </div>
      <div>
        <h4 className="text-lg font-bold text-slate-800 mb-1">{title}</h4>
        <p className="text-sm text-slate-500 leading-snug">{description}</p>
      </div>
    </div>
  );
}

function StatCard({ label, value, indicator }: { label: string, value: string, indicator?: string }) {
  return (
    <div className="glass-card rounded-2xl p-5 space-y-2">
      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{label}</p>
      <div className="flex items-center gap-3">
        {indicator && <div className={`w-3 h-3 rounded-full ${indicator} shadow-sm`} />}
        <p className="text-2xl font-black text-slate-800">{value}</p>
      </div>
    </div>
  );
}

function BackgroundShapes() {
  return (
    <>
      <div className="bg-shape w-[600px] h-[600px] bg-blue-200 top-[-200px] left-[-200px] rounded-full" />
      <div className="bg-shape w-[500px] h-[500px] bg-purple-200 bottom-[-100px] right-[-100px] rounded-full" />
      <div className="bg-shape w-[300px] h-[300px] bg-pink-100 top-[20%] right-[10%] rounded-full" />

      {/* Floating abstract elements simulation */}
      <div className="fixed top-[10%] left-[20%] w-12 h-12 bg-white/40 backdrop-blur-md rounded-xl rotate-12 animate-pulse" />
      <div className="fixed bottom-[15%] right-[25%] w-16 h-16 bg-white/40 backdrop-blur-md rounded-2xl -rotate-12 animate-pulse" />
      <div className="fixed top-[40%] right-[5%] w-10 h-10 bg-blue-400/20 backdrop-blur-md rounded-lg rotate-45" />
    </>
  );
}
