import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, Calendar, Clock, Download, Mail, Trash2, User, X } from 'lucide-react'
import { useEmail } from '../context/EmailContext'

export default function EmailView() {
  const { selectedMessage, setSelectedMessage, deleteMessage } = useEmail()

  if (!selectedMessage) return null

  const handleDelete = async () => {
    await deleteMessage(selectedMessage.id)
    setSelectedMessage(null)
  }

  const formattedDate = new Date(selectedMessage.received_at).toLocaleString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <AnimatePresence>
      <motion.div
        key="email-view-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={() => setSelectedMessage(null)}
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-dark-900/80 backdrop-blur-sm" />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 30 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 30 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          onClick={(e) => e.stopPropagation()}
          className="relative w-full max-w-2xl max-h-[85vh] glass rounded-2xl overflow-hidden gradient-border flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 flex-shrink-0">
            <motion.button
              onClick={() => setSelectedMessage(null)}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </motion.button>

            <div className="flex items-center gap-2">
              <motion.button
                onClick={handleDelete}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </motion.button>
              <motion.button
                onClick={() => setSelectedMessage(null)}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
              >
                <X className="w-5 h-5" />
              </motion.button>
            </div>
          </div>

          {/* Email Content */}
          <div className="overflow-y-auto flex-1 p-6">
            {/* Subject */}
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-xl font-bold text-white mb-4"
            >
              {selectedMessage.subject}
            </motion.h2>

            {/* Sender Info */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="flex items-start gap-3 mb-6 pb-6 border-b border-white/5"
            >
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center flex-shrink-0">
                <User className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">
                  {selectedMessage.from_address}
                </p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    <Mail className="w-3 h-3" />
                    to {selectedMessage.to_address}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    <Calendar className="w-3 h-3" />
                    {formattedDate}
                  </span>
                </div>
              </div>
            </motion.div>

            {/* Email Body */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {selectedMessage.html ? (
                <div
                  className="email-content"
                  dangerouslySetInnerHTML={{ __html: selectedMessage.html }}
                />
              ) : (
                <div className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap font-mono bg-dark-700/50 rounded-xl p-5">
                  {selectedMessage.body}
                </div>
              )}
            </motion.div>

            {/* Attachments */}
            {selectedMessage.attachments?.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
                className="mt-6 pt-6 border-t border-white/5"
              >
                <h3 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Attachments ({selectedMessage.attachments.length})
                </h3>
                <div className="flex flex-wrap gap-2">
                  {selectedMessage.attachments.map((att, i) => (
                    <div
                      key={i}
                      className="px-3 py-2 bg-white/5 rounded-lg text-sm text-slate-300 border border-white/5"
                    >
                      {att}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
