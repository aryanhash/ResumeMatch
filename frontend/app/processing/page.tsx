'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  CheckCircle2, Loader2, Clock, FileText, 
  Target, Sparkles, BookOpen, X, Lock,
  Settings, User
} from 'lucide-react'
import { useSession, signOut } from 'next-auth/react'
import Link from 'next/link'

// SECURITY: Validate API URL at build time
function getApiUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl && process.env.NODE_ENV === 'production') {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is required in production')
  }
  return apiUrl || 'http://localhost:8000'
}

interface ProgressUpdate {
  type: 'progress' | 'result' | 'error'
  workflow_id?: string
  step?: number
  step_name?: string
  status?: 'pending' | 'processing' | 'completed' | 'failed'
  message?: string
  details?: any
  timestamp?: string
  result?: any
  error?: string
}

interface Step {
  id: number
  name: string
  icon: any
  status: 'pending' | 'processing' | 'completed' | 'failed'
  message?: string
  duration?: string
  details?: any
}

export default function ProcessingPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { data: session } = useSession()
  
  const [workflowId, setWorkflowId] = useState<string>('')
  const [jobTitle, setJobTitle] = useState<string>('Senior Developer')
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState<string>('Initialization')
  const [estimatedTime, setEstimatedTime] = useState<number>(30)
  const [logs, setLogs] = useState<Array<{ time: string; message: string; type: 'info' | 'success' | 'error' }>>([])
  const [steps, setSteps] = useState<Step[]>([
    { id: 1, name: 'Parsing Resume', icon: FileText, status: 'pending' },
    { id: 2, name: 'Analyzing JD', icon: Target, status: 'pending' },
    { id: 3, name: 'Skill Matching', icon: Target, status: 'pending' },
    { id: 4, name: 'Skill Enhancement', icon: Sparkles, status: 'pending' },
    { id: 5, name: 'ATS Scoring (Oumi)', icon: Sparkles, status: 'pending' },
    { id: 6, name: 'ATS Scoring', icon: Target, status: 'pending' },
    { id: 7, name: 'AI Rewrite', icon: Sparkles, status: 'pending' },
    { id: 8, name: 'Cover Letter', icon: FileText, status: 'pending' },
    { id: 9, name: 'Explanation', icon: BookOpen, status: 'pending' },
    { id: 10, name: 'Project Recommendations', icon: BookOpen, status: 'pending' },
  ])
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string>('')
  const [isComplete, setIsComplete] = useState(false)
  
  const logsEndRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  
  const scrollLogsToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }
  
  useEffect(() => {
    scrollLogsToBottom()
  }, [logs])
  
  useEffect(() => {
    // Get resume and job description from URL params or sessionStorage
    const resumeText = searchParams.get('resume') || sessionStorage.getItem('resumeText') || ''
    const jobDescription = searchParams.get('jd') || sessionStorage.getItem('jobDescription') || ''
    
    if (!resumeText || !jobDescription) {
      router.push('/')
      return
    }
    
    // Extract job title from job description (simple extraction)
    const jdLines = jobDescription.split('\n').slice(0, 5)
    const titleMatch = jdLines.find(line => 
      line.toLowerCase().includes('title') || 
      line.toLowerCase().includes('position') ||
      line.toLowerCase().includes('role')
    )
    if (titleMatch) {
      const titleParts = titleMatch.split(/[:|•-]/)
      if (titleParts.length > 1) {
        setJobTitle(titleParts[1].trim())
      }
    }
    
    // Start processing
    startProcessing(resumeText, jobDescription)
    
    return () => {
      // Cleanup: close EventSource on unmount
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])
  
  const addLog = (message: string, type: 'info' | 'success' | 'error' = 'info') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
    setLogs(prev => [...prev, { time, message, type }])
  }
  
  const startProcessing = async (resumeText: string, jobDescription: string) => {
    try {
      const apiUrl = getApiUrl()
      
      // Use fetch with streaming
      // Generate workflow ID
      const workflowId = `FE-${Date.now().toString(36).toUpperCase()}`
      setWorkflowId(workflowId)
      
      addLog('Starting process...', 'info')
      
      // Add initial log
      const now = new Date()
      addLog(`[${now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}] Starting process...`, 'info')
      
      const response = await fetch(`${apiUrl}/process/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resume_text: resumeText,
          job_description: jobDescription,
        }),
      })
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`)
      }
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      if (!reader) {
        throw new Error('No response body')
      }
      
      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data: ProgressUpdate = JSON.parse(line.slice(6))
              handleProgressUpdate(data)
            } catch (e) {
              console.error('Failed to parse progress update:', e)
            }
          }
        }
      }
    } catch (err: any) {
      console.error('Processing error:', err)
      setError(err.message || 'Processing failed')
      addLog(`Error: ${err.message}`, 'error')
    }
  }
  
  const handleProgressUpdate = (update: ProgressUpdate) => {
    if (update.type === 'progress') {
      const stepName = update.step_name || ''
      const status = update.status || 'pending'
      const message = update.message || ''
      
      // Update current step
      if (status === 'processing') {
        setCurrentStep(stepName)
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
        addLog(`[${time}] > ${message}`, 'info')
        
        // Mark step as processing
        setSteps(prev => prev.map(step => {
          if (step.name === stepName) {
            return { ...step, status: 'processing' }
          }
          return step
        }))
      } else if (status === 'completed') {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
        addLog(`[${time}] > ${message}`, 'success')
        
        // Update step status
        setSteps(prev => {
          const updated = prev.map(step => {
            if (step.name === stepName) {
              return {
                ...step,
                status: 'completed',
                message: update.message,
                details: update.details
              }
            }
            return step
          })
          
          // Calculate progress based on completed steps
          const completedCount = updated.filter(s => s.status === 'completed').length
          const totalSteps = updated.length
          const newProgress = Math.min((completedCount / totalSteps) * 100, 95)
          setProgress(newProgress)
          
          return updated
        })
        
        // Update estimated time (decrease as we progress)
        setEstimatedTime(prev => Math.max(5, prev - 3))
      }
      
      // Add details to logs
      if (update.details) {
        const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
        if (update.details.required_skills && Array.isArray(update.details.required_skills)) {
          addLog(`[${time}] Required Skills: '${update.details.required_skills.slice(0, 10).join("', '")}'`)
        }
        if (update.details.match_percentage !== undefined) {
          addLog(`[${time}] Match Percentage: ${update.details.match_percentage}%`)
        }
        if (update.details.role) {
          addLog(`[${time}] Detected Role: ${update.details.role}`)
        }
        if (update.details.detected_format) {
          addLog(`[${time}] Detected Format: ${update.details.detected_format}`)
        }
      }
    } else if (update.type === 'result') {
      setResult(update.result)
      setIsComplete(true)
      setProgress(100)
      setCurrentStep('Complete')
      addLog('Processing complete!', 'success')
      
      // Store result in sessionStorage for results page
      sessionStorage.setItem('processingResult', JSON.stringify(update.result))
      
      // Navigate to results page after a short delay
      setTimeout(() => {
        router.push('/')
        // The main page will pick up the result from sessionStorage
      }, 2000)
    } else if (update.type === 'error') {
      setError(update.error || 'Unknown error')
      addLog(`Error: ${update.error}`, 'error')
    }
  }
  
  const getStepIcon = (step: Step) => {
    if (step.status === 'completed') {
      return <CheckCircle2 className="w-5 h-5 text-neon-green" />
    } else if (step.status === 'processing') {
      return <Loader2 className="w-5 h-5 text-electric-400 animate-spin" />
    } else {
      return <div className="w-5 h-5 rounded border-2 border-zinc-600" />
    }
  }
  
  const getStepStatusText = (step: Step) => {
    if (step.status === 'completed') {
      return step.duration || 'Completed'
    } else if (step.status === 'processing') {
      return 'Processing...'
    } else {
      return 'Pending'
    }
  }
  
  return (
    <main className="min-h-screen gradient-bg grid-overlay noise relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <motion.div
          className="absolute w-[600px] h-[600px] rounded-full bg-electric-600/20 blur-[120px]"
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{ top: '-20%', left: '-10%' }}
        />
      </div>

      {/* Header */}
      <header className="relative z-10 py-6 px-8">
        <nav className="max-w-7xl mx-auto flex items-center justify-between">
          <motion.div 
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-electric-500 to-cyber-500 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight">
              ResumeMatch<span className="text-electric-400">AI</span>
            </span>
          </motion.div>
          
          <motion.div 
            className="flex items-center gap-4"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <button className="p-2 rounded-lg glass hover:bg-white/10 transition-colors">
              <Settings className="w-5 h-5 text-zinc-400" />
            </button>
            {session ? (
              <div className="w-8 h-8 rounded-full bg-electric-600 flex items-center justify-center">
                {session.user?.name?.charAt(0) || session.user?.email?.charAt(0) || 'U'}
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center">
                <User className="w-4 h-4 text-zinc-400" />
              </div>
            )}
          </motion.div>
        </nav>
      </header>

      {/* Main Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-8 pb-20 pt-8">
        {/* Status Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="px-3 py-1 rounded-full bg-electric-600/20 text-electric-400 text-sm font-medium">
              PROCESSING
            </span>
            {workflowId && (
              <span className="text-sm text-zinc-500">Job ID: #{workflowId.slice(0, 8)}</span>
            )}
          </div>
          
          <h1 className="text-3xl md:text-4xl font-display font-bold mb-4">
            Optimizing Application for <span className="gradient-text">{jobTitle}</span>
          </h1>
          
          <div className="flex items-center gap-6 mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-zinc-400" />
              <span className="text-sm text-zinc-400">Est. time remaining: {estimatedTime}s</span>
              <Loader2 className="w-4 h-4 text-electric-400 animate-spin ml-2" />
            </div>
            <div className="text-2xl font-bold text-electric-400">{Math.round(progress)}%</div>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-electric-600 via-cyber-500 to-electric-400"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          
          <p className="text-sm text-zinc-400 mt-2">Current Step: {currentStep}</p>
        </div>
        
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Panel: Optimization Pipeline */}
          <div className="lg:col-span-1">
            <div className="glass rounded-2xl p-6">
              <h2 className="font-display text-lg font-semibold mb-4">Optimization Pipeline</h2>
              <div className="space-y-4">
                {steps.map((step) => (
                  <div
                    key={step.id}
                    className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                      step.status === 'processing' ? 'bg-electric-600/10' : ''
                    }`}
                  >
                    {getStepIcon(step)}
                    <div className="flex-1">
                      <div className="text-sm font-medium text-zinc-300">{step.name}</div>
                      <div className="text-xs text-zinc-500">{getStepStatusText(step)}</div>
                      {step.details && step.details.role && (
                        <div className="text-xs text-zinc-500 mt-1">Keywords Extracted</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              
              <button
                onClick={() => router.push('/')}
                className="w-full mt-6 flex items-center justify-center gap-2 px-4 py-2 rounded-lg glass hover:bg-white/10 transition-colors text-sm text-zinc-400"
              >
                <X className="w-4 h-4" />
                Cancel Process
              </button>
            </div>
          </div>
          
          {/* Right Panels: Live Logs and Results Preview */}
          <div className="lg:col-span-2 space-y-6">
            {/* Live Logs */}
            <div className="glass rounded-2xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-lg font-semibold">live_logs.txt</h2>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                </div>
              </div>
              
              <div className="bg-midnight-900/50 rounded-lg p-4 font-mono text-xs h-64 overflow-y-auto">
                {logs.length === 0 ? (
                  <div className="text-zinc-600">Waiting for logs...</div>
                ) : (
                  <>
                    {logs.map((log, i) => (
                      <div
                        key={i}
                        className={`mb-1 ${
                          log.type === 'success' ? 'text-neon-green' :
                          log.type === 'error' ? 'text-red-400' :
                          'text-zinc-400'
                        }`}
                      >
                        <span className="text-zinc-600">[{log.time}]</span> {log.message}
                      </div>
                    ))}
                    <div ref={logsEndRef} className="h-1" />
                    {!isComplete && (
                      <div className="text-electric-400 animate-pulse">_</div>
                    )}
                  </>
                )}
              </div>
            </div>
            
            {/* Results Preview */}
            <div className="glass rounded-2xl p-6 relative">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-lg font-semibold">Results Preview</h2>
                {!isComplete && (
                  <span className="px-2 py-1 rounded-full bg-zinc-800 text-xs text-zinc-500 flex items-center gap-1">
                    <Lock className="w-3 h-3" />
                    Locked
                  </span>
                )}
              </div>
              
              {isComplete && result ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-midnight-900/50">
                    <div className="text-sm text-zinc-400 mb-2">ATS Score</div>
                    <div className="text-3xl font-bold text-electric-400">
                      {result.ats_score?.overall_score || 'N/A'}
                    </div>
                  </div>
                  <div className="text-sm text-zinc-400">
                    Results are ready! Redirecting to detailed view...
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-48 text-zinc-600">
                  <FileText className="w-12 h-12 mb-4 opacity-50" />
                  <div className="text-sm">Generating...</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 py-4 px-8 border-t border-zinc-800/50">
        <div className="max-w-7xl mx-auto flex items-center justify-end">
          <div className="text-xs text-zinc-500">
            Powered by ResumeMatch AI v2.4.0
          </div>
        </div>
      </footer>
    </main>
  )
}
