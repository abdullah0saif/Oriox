import { useCallback } from 'react'
import AnimatedBackground from './components/AnimatedBackground'
import EmailGenerator from './components/EmailGenerator'
import EmailView from './components/EmailView'
import Features from './components/Features'
import Footer from './components/Footer'
import Header from './components/Header'
import Inbox from './components/Inbox'
import ToastContainer from './components/Toast'
import { EmailProvider } from './context/EmailContext'
import { useToast } from './hooks/useToast'

function AppContent() {
  const { toasts, addToast, removeToast } = useToast()

  const handleToast = useCallback((message, type) => {
    addToast(message, type)
  }, [addToast])

  return (
    <>
      <AnimatedBackground />
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <EmailView />

      <div className="relative z-10 min-h-screen flex flex-col">
        <Header />

        <main className="flex-1 px-4 sm:px-6 py-8">
          <div className="max-w-2xl mx-auto">
            <EmailGenerator onToast={handleToast} />
            <Inbox />
          </div>

          <div className="max-w-5xl mx-auto">
            <Features />
          </div>
        </main>

        <Footer />
      </div>
    </>
  )
}

export default function App() {
  return (
    <EmailProvider>
      <AppContent />
    </EmailProvider>
  )
}
