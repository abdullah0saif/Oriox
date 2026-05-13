import { AnimatePresence, motion } from 'framer-motion'
import { Inbox as InboxIcon, Mail, MailOpen, RefreshCw, Trash2 } from 'lucide-react'
import { useEmail } from '../context/EmailContext'

export default function Inbox() {
  const {
    emailAddress,
    messages,
    loading,
    fetchMessages,
    readMessage,
    deleteMessage,
    unreadCount,
  } = useEmail()

  if (!emailAddress) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="mt-6"
    >
      <div className="glass rounded-2xl overflow-hidden gradient-border">
        {/* Inbox Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-white">Inbox</h2>
            <AnimatePresence>
              {unreadCount > 0 && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0 }}
                  className="flex items-center justify-center w-6 h-6 rounded-full bg-accent-blue/20 text-accent-cyan text-xs font-bold"
                >
                  {unreadCount}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
          <motion.button
            onClick={fetchMessages}
            whileHover={{ scale: 1.1, rotate: 90 }}
            whileTap={{ scale: 0.9 }}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </motion.button>
        </div>

        {/* Message List */}
        <div className="divide-y divide-white/5">
          <AnimatePresence>
            {messages.length === 0 ? (
              <EmptyInbox />
            ) : (
              messages.map((message, index) => (
                <MessageRow
                  key={message.id}
                  message={message}
                  index={index}
                  onRead={readMessage}
                  onDelete={deleteMessage}
                />
              ))
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )
}

function MessageRow({ message, index, onRead, onDelete }) {
  const timeAgo = getTimeAgo(message.received_at)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20, height: 0 }}
      transition={{
        duration: 0.4,
        delay: index * 0.05,
        ease: [0.16, 1, 0.3, 1],
      }}
      onClick={() => onRead(message.id)}
      className={`group flex items-start gap-4 px-6 py-4 cursor-pointer transition-all duration-200 hover:bg-white/[0.03] ${
        !message.is_read ? 'bg-accent-blue/[0.03]' : ''
      }`}
    >
      <div className="flex-shrink-0 mt-1">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
          !message.is_read
            ? 'bg-accent-blue/15 text-accent-cyan'
            : 'bg-white/5 text-slate-500'
        }`}>
          {!message.is_read ? (
            <Mail className="w-4 h-4" />
          ) : (
            <MailOpen className="w-4 h-4" />
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`text-sm font-medium truncate ${
            !message.is_read ? 'text-white' : 'text-slate-300'
          }`}>
            {message.from_address}
          </span>
          {!message.is_read && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="w-2 h-2 rounded-full bg-accent-cyan flex-shrink-0"
            />
          )}
        </div>
        <p className={`text-sm mb-1 truncate ${
          !message.is_read ? 'text-slate-200 font-medium' : 'text-slate-400'
        }`}>
          {message.subject}
        </p>
        <p className="text-xs text-slate-500 email-line-clamp">
          {message.body.substring(0, 120)}...
        </p>
      </div>

      <div className="flex flex-col items-end gap-2 flex-shrink-0">
        <span className="text-xs text-slate-500">{timeAgo}</span>
        <motion.button
          onClick={(e) => {
            e.stopPropagation()
            onDelete(message.id)
          }}
          whileHover={{ scale: 1.2 }}
          whileTap={{ scale: 0.8 }}
          className="p-1.5 rounded-md text-slate-600 opacity-0 group-hover:opacity-100 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </motion.button>
      </div>
    </motion.div>
  )
}

function EmptyInbox() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2 }}
      className="py-16 text-center"
    >
      <motion.div
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/5 mb-4"
      >
        <InboxIcon className="w-8 h-8 text-slate-600" />
      </motion.div>
      <p className="text-slate-400 font-medium mb-1">No emails yet</p>
      <p className="text-slate-500 text-sm">
        Incoming emails will appear here automatically
      </p>
    </motion.div>
  )
}

function getTimeAgo(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)

  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}
