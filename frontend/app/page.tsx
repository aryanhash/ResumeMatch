'use client'

import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Upload, FileText, Briefcase, Sparkles, ArrowRight, 
  CheckCircle2, AlertCircle, TrendingUp, Download,
  Zap, Target, Award, BookOpen,
  ChevronDown, X, Loader2
} from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import Link from 'next/link'
import { useSession, signOut } from 'next-auth/react'

// SECURITY: Validate API URL at build time
function getApiUrl(): string {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL
  if (!apiUrl && process.env.NODE_ENV === 'production') {
    throw new Error('NEXT_PUBLIC_API_URL environment variable is required in production')
  }
  return apiUrl || 'http://localhost:8000'
}

// Types
interface ATSScore {
  overall_score: number
  bucket: string
  skill_match_score: number
  keyword_score: number
  formatting_score: number
  experience_alignment_score: number
  issues: Array<{
    category: string
    issue: string
    severity: string
    suggestion: string
  }>
  missing_keywords: string[]
  recommendations: string[]
}

interface GapAnalysis {
  matching_skills: string[]
  missing_skills: Array<{ skill: string; importance: string }>
  overall_match_percentage: number
  strengths: string[]
  weaknesses: string[]
}

interface CoverLetter {
  content: string
  word_count: number
}

interface ProjectRecommendation {
  name: string
  description: string
  skills_covered: string[]
  difficulty: string
  estimated_time: string
}

interface Result {
  parsed_resume: {
    name: string
    email?: string
    phone?: string
    location?: string
    linkedin?: string
    github?: string
    skills: string[]
    experience: Array<{
      title: string
      company: string
      duration: string
      description: string[]
    }>
    education: Array<{
      degree: string
      field_of_study?: string
      institution: string
      year?: string
      gpa?: string
    }>
    projects: Array<{
      name: string
      description: string
      technologies: string[]
      impact?: string
    }>
    certifications: string[]
  }
  parsed_jd: {
    role: string
    company: string
  }
  ats_score: ATSScore
  gap_analysis: GapAnalysis
  cover_letter: CoverLetter
  rewritten_resume: {
    summary: string
    reordered_skills: string[]
    improved_bullets: Array<{
      original: string
      improved: string
      impact_added: boolean
    }>
  }
  explanation: {
    recruiter_perspective: string
    what_stands_out: string[]
    red_flags: string[]
  }
  project_recommendations: {
    recommended_projects: ProjectRecommendation[]
    learning_paths: Array<{ skill: string; timeline: string }>
  }
}

export default function Home() {
  const { data: session } = useSession()
  const [step, setStep] = useState(1)
  const [resumeText, setResumeText] = useState('')
  const [resumeFileName, setResumeFileName] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [error, setError] = useState('')
  
  // Check for result from processing page
  useEffect(() => {
    const checkForResult = () => {
      const storedResult = sessionStorage.getItem('processingResult')
      if (storedResult) {
        try {
          const parsedResult = JSON.parse(storedResult)
          setResult(parsedResult)
          setStep(3)
          sessionStorage.removeItem('processingResult')
        } catch (e) {
          console.error('Failed to parse stored result:', e)
        }
      }
    }
    
    // Check immediately
    checkForResult()
    
    // Also check periodically and on focus (in case user navigated back)
    const interval = setInterval(checkForResult, 1000)
    window.addEventListener('focus', checkForResult)
    return () => {
      clearInterval(interval)
      window.removeEventListener('focus', checkForResult)
    }
  }, [])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (file) {
      setResumeFileName(file.name)
      setError('')
      
      const fileExtension = file.name.split('.').pop()?.toLowerCase()
      
      // For TXT files, read directly
      if (fileExtension === 'txt') {
        const reader = new FileReader()
        reader.onload = () => {
          setResumeText(reader.result as string)
          console.log(`📄 Loaded TXT file: ${file.name}, ${(reader.result as string).length} chars`)
        }
        reader.readAsText(file)
      } 
      // For PDF and DOCX, send to backend for proper parsing
      else if (fileExtension === 'pdf' || fileExtension === 'docx') {
        console.log(`📤 Sending ${fileExtension.toUpperCase()} file to backend for parsing...`)
        
        try {
          const apiUrl = getApiUrl()
          const formData = new FormData()
          formData.append('file', file)
          
          const response = await fetch(`${apiUrl}/parse-file`, {
            method: 'POST',
            body: formData,
          })
          
          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || 'Failed to parse file')
          }
          
          const data = await response.json()
          if (data.success && data.text) {
            setResumeText(data.text)
            console.log(`✅ Parsed ${fileExtension.toUpperCase()}: ${data.text.length} chars extracted`)
          } else {
            throw new Error('No text extracted from file')
          }
        } catch (err: any) {
          console.error('❌ File parsing failed:', err)
          setError(`Failed to parse ${fileExtension.toUpperCase()} file: ${err.message}. Please try a different file or paste your resume as text.`)
          setResumeFileName('')
        }
      } else {
        setError('Unsupported file format. Please use PDF, DOCX, or TXT files.')
        setResumeFileName('')
      }
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.txt'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1
  })

  const handleProcess = async () => {
    if (!resumeText || !jobDescription) {
      setError('Please provide both resume and job description')
      return
    }

    setIsProcessing(true)
    setError('')

    console.log('🚀 Starting resume processing...')
    console.log(`📄 Resume length: ${resumeText.length} characters`)
    console.log(`📋 Job description length: ${jobDescription.length} characters`)

    try {
      // Store data in sessionStorage for processing page
      sessionStorage.setItem('resumeText', resumeText)
      sessionStorage.setItem('jobDescription', jobDescription)
      
      // Navigate to processing page
      window.location.href = '/processing'
    } catch (err: any) {
      console.error('❌ Navigation error:', err)
      setError(`Error: ${err.message}`)
      setIsProcessing(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-neon-green'
    if (score >= 60) return 'text-neon-yellow'
    if (score >= 40) return 'text-neon-orange'
    return 'text-neon-pink'
  }

  const getScoreGradient = (score: number) => {
    if (score >= 80) return 'from-emerald-500 to-cyan-500'
    if (score >= 60) return 'from-yellow-500 to-orange-500'
    if (score >= 40) return 'from-orange-500 to-red-500'
    return 'from-red-500 to-pink-500'
  }

  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadFormat, setDownloadFormat] = useState<'pdf' | 'word'>('pdf')

  const downloadResume = async (format: 'pdf' | 'word' = 'pdf') => {
    // Get resume text and job description from state or sessionStorage
    const resumeTextToUse = resumeText || sessionStorage.getItem('resumeText') || ''
    const jobDescriptionToUse = jobDescription || sessionStorage.getItem('jobDescription') || ''
    
    if (!resumeTextToUse || !jobDescriptionToUse) {
      setError('Resume or job description not found. Please try processing again.')
      return
    }
    
    setIsDownloading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const endpoint = format === 'pdf' ? '/download/resume/pdf' : '/download/resume/word'
      
      console.log(`📥 Downloading resume as ${format.toUpperCase()}...`)
      
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resume_text: resumeTextToUse,
          job_description: jobDescriptionToUse,
        }),
      })
      
      if (!response.ok) {
        throw new Error(`Download failed: ${response.status}`)
      }
      
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = format === 'pdf' 
        ? `optimized_resume_${result?.parsed_jd.role.replace(/\s+/g, '_') || 'resume'}.pdf`
        : `optimized_resume_${result?.parsed_jd.role.replace(/\s+/g, '_') || 'resume'}.docx`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      console.log(`✅ Resume downloaded successfully as ${format.toUpperCase()}`)
    } catch (err) {
      console.error('Download failed:', err)
      setError(`Failed to download resume. Please try again.`)
    } finally {
      setIsDownloading(false)
    }
  }

  const downloadCoverLetter = async () => {
    // Get resume text and job description from state or sessionStorage
    const resumeTextToUse = resumeText || sessionStorage.getItem('resumeText') || ''
    const jobDescriptionToUse = jobDescription || sessionStorage.getItem('jobDescription') || ''
    
    if (!resumeTextToUse || !jobDescriptionToUse) {
      setError('Resume or job description not found. Please try processing again.')
      return
    }
    
    setIsDownloading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      
      console.log('📥 Downloading cover letter as PDF...')
      
      const response = await fetch(`${apiUrl}/download/cover-letter`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resume_text: resumeTextToUse,
          job_description: jobDescriptionToUse,
        }),
      })
      
      if (!response.ok) {
        // Fallback to text download if PDF endpoint fails
        console.log('PDF endpoint not available, downloading as text...')
        const blob = new Blob([result?.cover_letter.content || ''], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `cover_letter_${result?.parsed_jd.role.replace(/\s+/g, '_') || 'letter'}.txt`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        return
      }
      
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `cover_letter_${result?.parsed_jd.role.replace(/\s+/g, '_') || 'letter'}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      console.log('✅ Cover letter downloaded successfully')
    } catch (err) {
      console.error('Download failed:', err)
      // Fallback to text download
      if (result?.cover_letter.content) {
        const blob = new Blob([result.cover_letter.content], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `cover_letter_${result.parsed_jd.role.replace(/\s+/g, '_')}.txt`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
    } finally {
      setIsDownloading(false)
    }
  }

  const generateResumeText = (data: Result) => {
    const { parsed_resume, rewritten_resume, gap_analysis } = data
    
    let resume = ''
    
    // Header
    if (parsed_resume.name) resume += `${parsed_resume.name.toUpperCase()}\n`
    const contactInfo = [parsed_resume.email, parsed_resume.phone, parsed_resume.location].filter(Boolean)
    if (contactInfo.length) resume += `${contactInfo.join(' | ')}\n`
    if (parsed_resume.linkedin) resume += `LinkedIn: ${parsed_resume.linkedin}\n`
    if (parsed_resume.github) resume += `GitHub: ${parsed_resume.github}\n`
    resume += '\n'
    
    // Summary
    resume += '─'.repeat(60) + '\n'
    resume += 'PROFESSIONAL SUMMARY\n'
    resume += '─'.repeat(60) + '\n'
    resume += `${rewritten_resume.summary}\n\n`
    
    // Skills (reordered for ATS)
    resume += '─'.repeat(60) + '\n'
    resume += 'TECHNICAL SKILLS\n'
    resume += '─'.repeat(60) + '\n'
    resume += `${rewritten_resume.reordered_skills.join(', ')}\n\n`
    
    // Experience
    if (parsed_resume.experience.length > 0) {
      resume += '─'.repeat(60) + '\n'
      resume += 'PROFESSIONAL EXPERIENCE\n'
      resume += '─'.repeat(60) + '\n'
      
      for (const exp of parsed_resume.experience) {
        resume += `\n${exp.title} | ${exp.company}\n`
        resume += `${exp.duration}\n`
        
        // Use improved bullets if available
        const improvedMap = new Map(
          rewritten_resume.improved_bullets.map(b => [b.original, b.improved])
        )
        
        for (const bullet of exp.description) {
          const improvedBullet = improvedMap.get(bullet) || bullet
          resume += `• ${improvedBullet}\n`
        }
      }
      resume += '\n'
    }
    
    // Projects
    if (parsed_resume.projects.length > 0) {
      resume += '─'.repeat(60) + '\n'
      resume += 'PROJECTS\n'
      resume += '─'.repeat(60) + '\n'
      
      for (const proj of parsed_resume.projects) {
        resume += `\n${proj.name}`
        if (proj.technologies.length) resume += ` | ${proj.technologies.slice(0, 4).join(', ')}`
        resume += '\n'
        resume += `${proj.description}\n`
        if (proj.impact) resume += `• Impact: ${proj.impact}\n`
      }
      resume += '\n'
    }
    
    // Education
    if (parsed_resume.education.length > 0) {
      resume += '─'.repeat(60) + '\n'
      resume += 'EDUCATION\n'
      resume += '─'.repeat(60) + '\n'
      
      for (const edu of parsed_resume.education) {
        resume += `${edu.degree}`
        if (edu.field_of_study) resume += ` in ${edu.field_of_study}`
        resume += ` | ${edu.institution}`
        if (edu.year) resume += ` | ${edu.year}`
        if (edu.gpa) resume += ` | GPA: ${edu.gpa}`
        resume += '\n'
      }
      resume += '\n'
    }
    
    // Certifications
    if (parsed_resume.certifications.length > 0) {
      resume += '─'.repeat(60) + '\n'
      resume += 'CERTIFICATIONS\n'
      resume += '─'.repeat(60) + '\n'
      resume += `${parsed_resume.certifications.join(', ')}\n`
    }
    
    return resume
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
        <motion.div
          className="absolute w-[500px] h-[500px] rounded-full bg-cyber-500/20 blur-[100px]"
          animate={{
            x: [0, -80, 0],
            y: [0, 80, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{ bottom: '-10%', right: '-5%' }}
        />
        <motion.div
          className="absolute w-[400px] h-[400px] rounded-full bg-neon-pink/10 blur-[80px]"
          animate={{
            x: [0, 50, 0],
            y: [0, -30, 0],
          }}
          transition={{
            duration: 18,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{ top: '40%', left: '50%' }}
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
            {session ? (
              <>
                <div className="flex items-center gap-3">
                  {session.user?.image ? (
                    <img 
                      src={session.user.image} 
                      alt={session.user.name || 'User'} 
                      className="w-8 h-8 rounded-full border-2 border-electric-500"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-electric-600 flex items-center justify-center text-sm font-medium">
                      {session.user?.name?.charAt(0) || session.user?.email?.charAt(0) || 'U'}
                    </div>
                  )}
                  <span className="text-sm text-zinc-300 hidden md:block">
                    {session.user?.name || session.user?.email}
                  </span>
                </div>
                <button
                  onClick={() => signOut()}
                  className="text-sm text-zinc-400 hover:text-white transition-colors px-4 py-2"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link 
                  href="/signin" 
                  className="text-sm text-zinc-300 hover:text-white transition-colors px-4 py-2"
                >
                  Sign In
                </Link>
                <Link 
                  href="/signup" 
                  className="text-sm font-medium text-white bg-electric-600 hover:bg-electric-500 transition-colors px-5 py-2.5 rounded-lg"
                >
                  Sign Up
                </Link>
              </>
            )}
          </motion.div>
        </nav>
      </header>

      {/* Main Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-8 pb-20">
        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div
              key="step1"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="py-16"
            >
              {/* Hero Section */}
              <div className="text-center mb-16">
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass mb-6"
                >
                  <Zap className="w-4 h-4 text-neon-yellow" />
                  <span className="text-sm text-zinc-300">Powered by AI Multi-Agent System</span>
                </motion.div>
                
                <motion.h1
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="font-display text-5xl md:text-7xl font-bold mb-6 leading-tight"
                >
                  Transform Your Resume
                  <br />
                  <span className="gradient-text">Into Interview Invites</span>
                </motion.h1>
                
                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="text-lg text-zinc-400 max-w-2xl mx-auto mb-8"
                >
                  Our AI agents analyze, score, and optimize your resume for any job. 
                  Get ATS-friendly formatting, personalized cover letters, and actionable insights.
                </motion.p>

                {/* Feature pills */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="flex flex-wrap justify-center gap-3 mb-12"
                >
                  {[
                    { icon: Target, text: 'ATS Optimization' },
                    { icon: TrendingUp, text: 'Skill Gap Analysis' },
                    { icon: FileText, text: 'Cover Letters' },
                    { icon: BookOpen, text: 'Project Ideas' },
                  ].map((item, i) => (
                    <div
                      key={item.text}
                      className="flex items-center gap-2 px-4 py-2 rounded-full glass-light"
                    >
                      <item.icon className="w-4 h-4 text-electric-400" />
                      <span className="text-sm">{item.text}</span>
                    </div>
                  ))}
                </motion.div>
              </div>

              {/* Upload Section */}
              <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="max-w-4xl mx-auto"
              >
                <div className="glass rounded-3xl p-8 glow-purple">
                  <div className="grid md:grid-cols-2 gap-8">
                    {/* Resume Upload */}
                    <div>
                      <label className="flex items-center gap-2 text-sm font-medium mb-3 text-zinc-300">
                        <FileText className="w-4 h-4" />
                        Your Resume
                      </label>
                      <div
                        {...getRootProps()}
                        className={`
                          relative h-48 rounded-2xl border-2 border-dashed transition-all cursor-pointer
                          ${isDragActive 
                            ? 'border-electric-500 bg-electric-500/10' 
                            : 'border-zinc-700 hover:border-zinc-500 hover:bg-white/5'
                          }
                        `}
                      >
                        <input {...getInputProps()} />
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                          {resumeFileName ? (
                            <>
                              <CheckCircle2 className="w-10 h-10 text-neon-green mb-3" />
                              <p className="text-sm font-medium">{resumeFileName}</p>
                              <p className="text-xs text-zinc-500 mt-1">Click to replace</p>
                            </>
                          ) : (
                            <>
                              <Upload className="w-10 h-10 text-zinc-500 mb-3" />
                              <p className="text-sm text-zinc-400">
                                {isDragActive ? 'Drop your resume here' : 'Drag & drop or click to upload'}
                              </p>
                              <p className="text-xs text-zinc-600 mt-1">PDF, DOCX, or TXT</p>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Job Description */}
                    <div>
                      <label className="flex items-center gap-2 text-sm font-medium mb-3 text-zinc-300">
                        <Briefcase className="w-4 h-4" />
                        Job Description
                      </label>
                      <textarea
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder="Paste the job description here..."
                        className="w-full h-[calc(100%-2rem)] min-h-[320px] px-4 py-3 bg-midnight-900/50 border border-zinc-800 rounded-xl text-sm resize-none placeholder:text-zinc-600 focus:border-electric-500/50"
                      />
                    </div>
                  </div>

                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3"
                    >
                      <AlertCircle className="w-5 h-5 text-red-400" />
                      <p className="text-sm text-red-300">{error}</p>
                    </motion.div>
                  )}

                  <motion.button
                    onClick={handleProcess}
                    disabled={isProcessing || (!resumeText || !jobDescription)}
                    className={`
                      w-full mt-8 py-4 px-8 rounded-xl font-medium text-lg
                      flex items-center justify-center gap-3
                      transition-all duration-300 btn-glow
                      ${isProcessing || !resumeText || !jobDescription
                        ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                        : 'bg-gradient-to-r from-electric-600 to-cyber-600 hover:from-electric-500 hover:to-cyber-500 text-white glow-purple'
                      }
                    `}
                    whileHover={{ scale: isProcessing ? 1 : 1.02 }}
                    whileTap={{ scale: isProcessing ? 1 : 0.98 }}
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Analyzing with AI Agents...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        Optimize My Resume
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </motion.button>
                </div>
              </motion.div>

              {/* Agent Flow Visualization */}
              <motion.div
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
                className="mt-20"
              >
                <h3 className="text-center font-display text-2xl font-bold mb-8">
                  <span className="gradient-text">9 AI Agents</span> Working For You
                </h3>
                <div className="flex flex-wrap justify-center gap-4">
                  {[
                    'Resume Parser',
                    'JD Analyzer', 
                    'Gap Analysis',
                    'Skill Agent',
                    'ATS Scorer',
                    'Resume Rewriter',
                    'Cover Letter',
                    'Explainer',
                    'Project Advisor'
                  ].map((agent, i) => (
                    <motion.div
                      key={agent}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.8 + i * 0.05 }}
                      className="px-4 py-2 rounded-lg glass-light text-sm font-mono text-zinc-300"
                    >
                      {agent}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </motion.div>
          )}

          {step === 3 && result && (
            <motion.div
              key="step3"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="py-8"
            >
              {/* Results Header */}
              <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                <div>
                  <h2 className="font-display text-3xl font-bold">
                    Analysis Complete
                  </h2>
                  <p className="text-zinc-400 mt-1">
                    For {result.parsed_jd.role} {result.parsed_jd.company && `at ${result.parsed_jd.company}`}
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  {/* PDF Download Button */}
                  <button
                    onClick={() => downloadResume('pdf')}
                    disabled={isDownloading}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 transition-all font-medium disabled:opacity-50"
                  >
                    <Download className="w-4 h-4" />
                    {isDownloading ? 'Generating...' : 'Download PDF'}
                  </button>
                  {/* Word Download Button */}
                  <button
                    onClick={() => downloadResume('word')}
                    disabled={isDownloading}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 transition-all font-medium disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    {isDownloading ? 'Generating...' : 'Download Word'}
                  </button>
                  {/* Cover Letter Download */}
                  <button
                    onClick={downloadCoverLetter}
                    disabled={isDownloading}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 transition-all font-medium disabled:opacity-50"
                  >
                    <FileText className="w-4 h-4" />
                    Cover Letter
                  </button>
                  <button
                    onClick={() => {
                      setStep(1)
                      setResult(null)
                      setResumeText('')
                      setResumeFileName('')
                      setJobDescription('')
                    }}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg glass hover:bg-white/10 transition-colors"
                  >
                    <X className="w-4 h-4" />
                    New Analysis
                  </button>
                </div>
              </div>

              {/* Score Card */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass rounded-3xl p-8 mb-8"
              >
                <div className="grid md:grid-cols-4 gap-8">
                  {/* Main Score */}
                  <div className="md:col-span-1 flex flex-col items-center justify-center">
                    <div className="relative w-40 h-40">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle
                          cx="80"
                          cy="80"
                          r="70"
                          fill="none"
                          stroke="rgba(255,255,255,0.1)"
                          strokeWidth="12"
                        />
                        <circle
                          cx="80"
                          cy="80"
                          r="70"
                          fill="none"
                          stroke="url(#scoreGradient)"
                          strokeWidth="12"
                          strokeLinecap="round"
                          strokeDasharray={440}
                          strokeDashoffset={440 - (440 * result.ats_score.overall_score) / 100}
                          className="transition-all duration-1000"
                        />
                        <defs>
                          <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stopColor="#8b5cf6" />
                            <stop offset="50%" stopColor="#06b6d4" />
                            <stop offset="100%" stopColor="#4ade80" />
                          </linearGradient>
                        </defs>
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className={`text-4xl font-display font-bold ${getScoreColor(result.ats_score.overall_score)}`}>
                          {result.ats_score.overall_score}
                        </span>
                        <span className="text-sm text-zinc-500">ATS Score</span>
                      </div>
                    </div>
                    <div className={`mt-4 px-4 py-2 rounded-full bg-gradient-to-r ${getScoreGradient(result.ats_score.overall_score)} text-sm font-medium`}>
                      {result.ats_score.bucket.replace('_', ' ').toUpperCase()}
                    </div>
                  </div>

                  {/* Component Scores */}
                  <div className="md:col-span-3 grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                      { label: 'Skill Match', value: result.ats_score.skill_match_score, icon: Target },
                      { label: 'Keywords', value: result.ats_score.keyword_score, icon: FileText },
                      { label: 'Formatting', value: result.ats_score.formatting_score, icon: CheckCircle2 },
                      { label: 'Experience', value: result.ats_score.experience_alignment_score, icon: Briefcase },
                    ].map((item) => (
                      <div key={item.label} className="p-4 rounded-2xl glass-light">
                        <div className="flex items-center gap-2 mb-3">
                          <item.icon className="w-4 h-4 text-zinc-400" />
                          <span className="text-xs text-zinc-400">{item.label}</span>
                        </div>
                        <div className="flex items-end gap-2">
                          <span className={`text-2xl font-bold ${getScoreColor(item.value)}`}>
                            {item.value}
                          </span>
                          <span className="text-zinc-500 text-sm mb-1">/100</span>
                        </div>
                        <div className="mt-2 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                          <motion.div
                            className={`h-full rounded-full bg-gradient-to-r ${getScoreGradient(item.value)}`}
                            initial={{ width: 0 }}
                            animate={{ width: `${item.value}%` }}
                            transition={{ duration: 1, delay: 0.5 }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>

              {/* Tabs */}
              <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
                {[
                  { id: 'overview', label: 'Overview', icon: TrendingUp },
                  { id: 'skills', label: 'Skills Analysis', icon: Target },
                  { id: 'cover', label: 'Cover Letter', icon: FileText },
                  { id: 'projects', label: 'Recommended Projects', icon: BookOpen },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg whitespace-nowrap transition-all
                      ${activeTab === tab.id 
                        ? 'bg-electric-600 text-white' 
                        : 'glass hover:bg-white/10 text-zinc-400'
                      }
                    `}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Content */}
              <AnimatePresence mode="wait">
                {activeTab === 'overview' && (
                  <motion.div
                    key="overview"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="grid md:grid-cols-2 gap-6"
                  >
                    {/* Recruiter Perspective */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <Award className="w-5 h-5 text-electric-400" />
                        Recruiter Perspective
                      </h3>
                      <p className="text-zinc-300 leading-relaxed">
                        {result.explanation.recruiter_perspective}
                      </p>
                    </div>

                    {/* What Stands Out */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-neon-green" />
                        What Stands Out
                      </h3>
                      <ul className="space-y-2">
                        {result.explanation.what_stands_out.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-zinc-300">
                            <CheckCircle2 className="w-4 h-4 text-neon-green mt-1 flex-shrink-0" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Improvements Needed */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-neon-orange" />
                        Areas to Improve
                      </h3>
                      <ul className="space-y-3">
                        {result.ats_score.issues.slice(0, 4).map((issue, i) => (
                          <li key={i} className="p-3 rounded-lg bg-midnight-900/50">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-xs px-2 py-0.5 rounded-full ${
                                issue.severity === 'high' ? 'bg-red-500/20 text-red-400' :
                                issue.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                                'bg-zinc-500/20 text-zinc-400'
                              }`}>
                                {issue.severity}
                              </span>
                              <span className="text-sm font-medium">{issue.category}</span>
                            </div>
                            <p className="text-sm text-zinc-400">{issue.issue}</p>
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Optimized Summary */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <FileText className="w-5 h-5 text-cyber-400" />
                        Optimized Summary
                      </h3>
                      <p className="text-zinc-300 leading-relaxed italic">
                        "{result.rewritten_resume.summary}"
                      </p>
                      <div className="mt-4 flex gap-3">
                        <button 
                          onClick={() => downloadResume('pdf')}
                          disabled={isDownloading}
                          className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/30 transition-colors disabled:opacity-50"
                        >
                          <Download className="w-4 h-4" />
                          PDF
                        </button>
                        <button 
                          onClick={() => downloadResume('word')}
                          disabled={isDownloading}
                          className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-blue-600/20 text-blue-400 hover:bg-blue-600/30 transition-colors disabled:opacity-50"
                        >
                          <FileText className="w-4 h-4" />
                          Word
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}

                {activeTab === 'skills' && (
                  <motion.div
                    key="skills"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="grid md:grid-cols-2 gap-6"
                  >
                    {/* Matching Skills */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-neon-green" />
                        Matching Skills ({result.gap_analysis.matching_skills.length})
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {result.gap_analysis.matching_skills.map((skill, i) => (
                          <span
                            key={i}
                            className="px-3 py-1.5 rounded-lg bg-neon-green/10 border border-neon-green/30 text-neon-green text-sm"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Missing Skills */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-neon-orange" />
                        Missing Skills ({result.gap_analysis.missing_skills.length})
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {result.gap_analysis.missing_skills.map((skill, i) => (
                          <span
                            key={i}
                            className={`px-3 py-1.5 rounded-lg text-sm ${
                              skill.importance === 'required'
                                ? 'bg-red-500/10 border border-red-500/30 text-red-400'
                                : 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
                            }`}
                          >
                            {skill.skill}
                            <span className="ml-1 text-xs opacity-60">({skill.importance})</span>
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Missing Keywords */}
                    <div className="glass rounded-2xl p-6 md:col-span-2">
                      <h3 className="font-display text-lg font-semibold mb-4 flex items-center gap-2">
                        <Target className="w-5 h-5 text-cyber-400" />
                        Add These Keywords
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {result.ats_score.missing_keywords.map((keyword, i) => (
                          <span
                            key={i}
                            className="px-3 py-1.5 rounded-lg bg-cyber-500/10 border border-cyber-500/30 text-cyan-400 text-sm"
                          >
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {activeTab === 'cover' && (
                  <motion.div
                    key="cover"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                  >
                    <div className="glass rounded-2xl p-8">
                      <div className="flex items-center justify-between mb-6">
                        <h3 className="font-display text-xl font-semibold">
                          Generated Cover Letter
                        </h3>
                        <div className="flex items-center gap-4">
                          <span className="text-sm text-zinc-400">
                            {result.cover_letter.word_count} words
                          </span>
                          <button 
                            onClick={downloadCoverLetter}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-electric-600 hover:bg-electric-500 transition-colors"
                          >
                            <Download className="w-4 h-4" />
                            Download
                          </button>
                        </div>
                      </div>
                      <div className="prose prose-invert max-w-none">
                        <div className="whitespace-pre-wrap text-zinc-300 leading-relaxed font-body">
                          {result.cover_letter.content}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}

                {activeTab === 'projects' && (
                  <motion.div
                    key="projects"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="space-y-6"
                  >
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {result.project_recommendations.recommended_projects.map((project, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.1 }}
                          className="glass rounded-2xl p-6 card-lift"
                        >
                          <div className="flex items-start justify-between mb-3">
                            <h4 className="font-display font-semibold text-lg">{project.name}</h4>
                            <span className={`text-xs px-2 py-1 rounded-full ${
                              project.difficulty === 'beginner' ? 'bg-green-500/20 text-green-400' :
                              project.difficulty === 'intermediate' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>
                              {project.difficulty}
                            </span>
                          </div>
                          <p className="text-sm text-zinc-400 mb-4">{project.description}</p>
                          <div className="flex flex-wrap gap-1 mb-4">
                            {project.skills_covered.map((skill, j) => (
                              <span key={j} className="text-xs px-2 py-1 rounded bg-electric-500/10 text-electric-300">
                                {skill}
                              </span>
                            ))}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-zinc-500">
                            <BookOpen className="w-3 h-3" />
                            {project.estimated_time}
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {/* Learning Paths */}
                    <div className="glass rounded-2xl p-6">
                      <h3 className="font-display text-lg font-semibold mb-4">Learning Paths</h3>
                      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {result.project_recommendations.learning_paths.map((path, i) => (
                          <div key={i} className="p-4 rounded-xl bg-midnight-900/50">
                            <div className="flex items-center gap-2 mb-2">
                              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-electric-500 to-cyber-500 flex items-center justify-center">
                                <BookOpen className="w-4 h-4" />
                              </div>
                              <span className="font-medium">{path.skill}</span>
                            </div>
                            <p className="text-xs text-zinc-500">{path.timeline}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer */}
      <footer className="relative z-10 py-8 px-8 border-t border-zinc-800/50">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-zinc-500 text-sm">
            <Sparkles className="w-4 h-4" />
            Built with AI Multi-Agent Technology
          </div>
          <div className="flex items-center gap-6 text-sm text-zinc-500">
            <span>🔒 Your data stays private</span>
            <span>🚫 No auto-submission</span>
            <span>✅ You control everything</span>
          </div>
        </div>
      </footer>
    </main>
  )
}

