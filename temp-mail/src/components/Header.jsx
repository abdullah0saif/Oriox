import { motion } from 'framer-motion'
import { Mail, Shield, Zap } from 'lucide-react'

export default function Header() {
  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="relative z-10 px-6 py-5"
    >
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <motion.div
          className="flex items-center gap-3"
          whileHover={{ scale: 1.02 }}
          transition={{ type: 'spring', stiffness: 400 }}
        >
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-blue via-accent-purple to-accent-cyan flex items-center justify-center">
              <Mail className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -inset-1 bg-gradient-to-br from-accent-blue via-accent-purple to-accent-cyan rounded-xl opacity-20 blur-md" />
          </div>
          <span className="text-xl font-bold tracking-tight">
            <span className="gradient-text">TempMail</span>
            <span className="text-slate-400">Box</span>
          </span>
        </motion.div>

        <div className="hidden sm:flex items-center gap-6">
          <Feature icon={<Shield className="w-4 h-4" />} text="100% Private" />
          <Feature icon={<Zap className="w-4 h-4" />} text="Instant Setup" />
        </div>
      </div>
    </motion.header>
  )
}

function Feature({ icon, text }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <span className="text-accent-cyan">{icon}</span>
      {text}
    </div>
  )
}
