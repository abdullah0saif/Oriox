import { motion } from 'framer-motion'
import { Clock, Eye, Globe, Lock, RefreshCw, Shield, Sparkles, Zap } from 'lucide-react'

const features = [
  {
    icon: <Zap className="w-5 h-5" />,
    title: 'Instant Creation',
    description: 'Generate a disposable email in one click. No sign-up required.',
    color: 'from-amber-500/20 to-orange-500/20',
    iconColor: 'text-amber-400',
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: 'Privacy First',
    description: 'Your real email stays hidden. No tracking, no data collection.',
    color: 'from-emerald-500/20 to-teal-500/20',
    iconColor: 'text-emerald-400',
  },
  {
    icon: <Clock className="w-5 h-5" />,
    title: 'Auto-Expiry',
    description: 'Emails self-destruct after 10 minutes. Zero trace left behind.',
    color: 'from-accent-blue/20 to-accent-cyan/20',
    iconColor: 'text-accent-cyan',
  },
  {
    icon: <RefreshCw className="w-5 h-5" />,
    title: 'Unlimited Addresses',
    description: 'Generate as many addresses as you need. Fresh inbox every time.',
    color: 'from-accent-purple/20 to-pink-500/20',
    iconColor: 'text-accent-purple',
  },
  {
    icon: <Eye className="w-5 h-5" />,
    title: 'Real-Time Inbox',
    description: 'Watch emails arrive instantly with live updates and notifications.',
    color: 'from-blue-500/20 to-indigo-500/20',
    iconColor: 'text-blue-400',
  },
  {
    icon: <Globe className="w-5 h-5" />,
    title: 'Works Everywhere',
    description: 'Use it for signups, verifications, or anything needing a quick email.',
    color: 'from-rose-500/20 to-pink-500/20',
    iconColor: 'text-rose-400',
  },
]

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.08,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.5,
      ease: [0.16, 1, 0.3, 1],
    },
  },
}

export default function Features() {
  return (
    <motion.section
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: '-100px' }}
      variants={containerVariants}
      className="mt-20 mb-12"
    >
      <motion.div variants={itemVariants} className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-blue/10 border border-accent-blue/20 mb-4">
          <Sparkles className="w-4 h-4 text-accent-cyan" />
          <span className="text-sm text-accent-cyan font-medium">Why TempMailBox?</span>
        </div>
        <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
          Simple, Secure, and <span className="gradient-text">Powerful</span>
        </h2>
        <p className="text-slate-400 max-w-lg mx-auto">
          Everything you need from a temporary email service, with a beautiful experience.
        </p>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.map((feature, i) => (
          <motion.div
            key={i}
            variants={itemVariants}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className="glass glass-hover rounded-xl p-6 group"
          >
            <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${feature.color} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
              <span className={feature.iconColor}>{feature.icon}</span>
            </div>
            <h3 className="text-white font-semibold mb-2">{feature.title}</h3>
            <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
          </motion.div>
        ))}
      </div>
    </motion.section>
  )
}
