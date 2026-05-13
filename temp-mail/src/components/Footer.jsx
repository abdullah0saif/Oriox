import { motion } from 'framer-motion'
import { Heart, Mail } from 'lucide-react'

export default function Footer() {
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 1 }}
      className="relative z-10 py-8 mt-12 border-t border-white/5"
    >
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Mail className="w-4 h-4 text-accent-blue" />
          <span className="gradient-text font-semibold">TempMailBox</span>
          <span>— Disposable emails, zero worries.</span>
        </div>
        <div className="flex items-center gap-1 text-sm text-slate-500">
          <span>Built with</span>
          <Heart className="w-3.5 h-3.5 text-red-400 fill-red-400" />
          <span>for your privacy</span>
        </div>
      </div>
    </motion.footer>
  )
}
