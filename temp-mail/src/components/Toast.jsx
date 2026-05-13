import { AnimatePresence, motion } from 'framer-motion'
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react'

const icons = {
  success: <CheckCircle className="w-5 h-5 text-emerald-400" />,
  error: <AlertCircle className="w-5 h-5 text-red-400" />,
  info: <Info className="w-5 h-5 text-accent-cyan" />,
}

const bgColors = {
  success: 'bg-emerald-500/10 border-emerald-500/20',
  error: 'bg-red-500/10 border-red-500/20',
  info: 'bg-accent-blue/10 border-accent-blue/20',
}

export default function ToastContainer({ toasts, onRemove }) {
  return (
    <div className="fixed top-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 100, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.9 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className={`pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl shadow-lg ${bgColors[toast.type] || bgColors.info}`}
          >
            {icons[toast.type] || icons.info}
            <span className="text-sm text-white font-medium">{toast.message}</span>
            <button
              onClick={() => onRemove(toast.id)}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/10 transition-colors ml-2"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
