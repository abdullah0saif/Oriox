import { AnimatePresence, motion } from 'framer-motion'
import { Check, Clock, Copy, Mail, RefreshCw, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useEmail } from '../context/EmailContext'

export default function EmailGenerator({ onToast }) {
  const {
    emailAddress,
    loading,
    timeRemaining,
    generateEmail,
    sendTestEmail,
    deleteEmail,
  } = useEmail()
  const [copied, setCopied] = useState(false)
  const [sending, setSending] = useState(false)

  const handleGenerate = async () => {
    const result = await generateEmail()
    if (result) {
      onToast('New temporary email created!', 'success')
    }
  }

  const handleCopy = async () => {
    if (!emailAddress) return
    try {
      await navigator.clipboard.writeText(emailAddress)
      setCopied(true)
      onToast('Email copied to clipboard!', 'success')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      onToast('Failed to copy email', 'error')
    }
  }

  const handleSendTest = async () => {
    setSending(true)
    const success = await sendTestEmail()
    if (success) {
      onToast('Test email sent! Check your inbox.', 'success')
    } else {
      onToast('Failed to send test email', 'error')
    }
    setSending(false)
  }

  const handleDelete = async () => {
    await deleteEmail()
    onToast('Email address deleted', 'info')
  }

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const progress = emailAddress ? (timeRemaining / 600) * 100 : 0

  return (
    <motion.div
      layout
      className="relative"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="glass rounded-2xl p-8 glow-blue gradient-border">
        <div className="text-center mb-6">
          <motion.h1
            className="text-3xl sm:text-4xl font-extrabold mb-3 text-balance"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <span className="gradient-text">Your Temporary Email</span>
          </motion.h1>
          <motion.p
            className="text-slate-400 text-sm sm:text-base max-w-md mx-auto"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            Protect your privacy with a disposable email address.
            No registration needed.
          </motion.p>
        </div>

        <AnimatePresence mode="wait">
          {emailAddress ? (
            <motion.div
              key="email-display"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            >
              {/* Email Address Display */}
              <div
                className="relative group cursor-pointer mb-5"
                onClick={handleCopy}
              >
                <div className="flex items-center gap-3 bg-dark-700/80 rounded-xl px-5 py-4 border border-white/5 hover:border-accent-blue/30 transition-all duration-300">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider font-medium">
                      Your email address
                    </p>
                    <p className="text-lg sm:text-xl font-mono font-semibold text-white truncate">
                      {emailAddress}
                    </p>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="flex-shrink-0 p-2.5 rounded-lg bg-accent-blue/10 text-accent-cyan hover:bg-accent-blue/20 transition-colors"
                  >
                    <AnimatePresence mode="wait">
                      {copied ? (
                        <motion.div
                          key="check"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          exit={{ scale: 0 }}
                        >
                          <Check className="w-5 h-5 text-emerald-400" />
                        </motion.div>
                      ) : (
                        <motion.div
                          key="copy"
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          exit={{ scale: 0 }}
                        >
                          <Copy className="w-5 h-5" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.button>
                </div>
              </div>

              {/* Timer Bar */}
              <div className="mb-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 text-sm text-slate-400">
                    <Clock className="w-4 h-4" />
                    <span>Expires in</span>
                  </div>
                  <span className={`text-sm font-mono font-semibold ${
                    timeRemaining < 60 ? 'text-red-400' :
                    timeRemaining < 180 ? 'text-amber-400' :
                    'text-accent-cyan'
                  }`}>
                    {formatTime(timeRemaining)}
                  </span>
                </div>
                <div className="h-1.5 bg-dark-700 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${
                      timeRemaining < 60 ? 'bg-gradient-to-r from-red-500 to-red-400' :
                      timeRemaining < 180 ? 'bg-gradient-to-r from-amber-500 to-amber-400' :
                      'bg-gradient-to-r from-accent-blue to-accent-cyan'
                    }`}
                    initial={{ width: '100%' }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3">
                <ActionButton
                  onClick={handleSendTest}
                  icon={<Send className="w-4 h-4" />}
                  text={sending ? 'Sending...' : 'Send Test Email'}
                  variant="primary"
                  disabled={sending}
                />
                <ActionButton
                  onClick={handleGenerate}
                  icon={<RefreshCw className="w-4 h-4" />}
                  text="New Address"
                  variant="secondary"
                  disabled={loading}
                />
                <ActionButton
                  onClick={handleDelete}
                  icon={<Trash2 className="w-4 h-4" />}
                  text="Delete"
                  variant="danger"
                />
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="generate-btn"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="text-center"
            >
              <motion.button
                onClick={handleGenerate}
                disabled={loading}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                className="relative group px-8 py-4 rounded-xl font-semibold text-white text-lg overflow-hidden disabled:opacity-50"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-accent-blue via-accent-purple to-accent-cyan opacity-90 group-hover:opacity-100 transition-opacity" />
                <div className="absolute inset-0 bg-gradient-to-r from-accent-blue via-accent-purple to-accent-cyan opacity-0 group-hover:opacity-40 blur-xl transition-opacity" />
                <span className="relative flex items-center gap-2">
                  {loading ? (
                    <RefreshCw className="w-5 h-5 animate-spin" />
                  ) : (
                    <Mail className="w-5 h-5" />
                  )}
                  {loading ? 'Generating...' : 'Generate Email Address'}
                </span>
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

function ActionButton({ onClick, icon, text, variant = 'secondary', disabled = false }) {
  const styles = {
    primary: 'bg-accent-blue/15 text-accent-cyan hover:bg-accent-blue/25 border-accent-blue/20',
    secondary: 'bg-white/5 text-slate-300 hover:bg-white/10 border-white/10',
    danger: 'bg-red-500/10 text-red-400 hover:bg-red-500/20 border-red-500/20',
  }

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium border transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed ${styles[variant]}`}
    >
      {icon}
      {text}
    </motion.button>
  )
}
