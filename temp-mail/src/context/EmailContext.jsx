import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

const EmailContext = createContext(null)

const API_BASE = '/api'

export function EmailProvider({ children }) {
  const [emailAddress, setEmailAddress] = useState(null)
  const [emailInfo, setEmailInfo] = useState(null)
  const [messages, setMessages] = useState([])
  const [selectedMessage, setSelectedMessage] = useState(null)
  const [loading, setLoading] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState(0)
  const wsRef = useRef(null)
  const pollingRef = useRef(null)

  const generateEmail = useCallback(async () => {
    setLoading(true)
    setSelectedMessage(null)
    setMessages([])
    try {
      const res = await fetch(`${API_BASE}/email/generate`)
      const data = await res.json()
      setEmailAddress(data.address)
      setEmailInfo(data)
      setTimeRemaining(data.ttl_seconds)
      return data
    } catch (err) {
      console.error('Failed to generate email:', err)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchMessages = useCallback(async () => {
    if (!emailAddress) return
    try {
      const res = await fetch(`${API_BASE}/email/${emailAddress}/messages`)
      if (res.ok) {
        const data = await res.json()
        setMessages(data)
      }
    } catch (err) {
      console.error('Failed to fetch messages:', err)
    }
  }, [emailAddress])

  const readMessage = useCallback(async (messageId) => {
    if (!emailAddress) return null
    try {
      const res = await fetch(`${API_BASE}/email/${emailAddress}/messages/${messageId}`)
      if (res.ok) {
        const data = await res.json()
        setSelectedMessage(data)
        setMessages(prev => prev.map(m => m.id === messageId ? { ...m, is_read: true } : m))
        return data
      }
    } catch (err) {
      console.error('Failed to read message:', err)
    }
    return null
  }, [emailAddress])

  const deleteMessage = useCallback(async (messageId) => {
    if (!emailAddress) return
    try {
      await fetch(`${API_BASE}/email/${emailAddress}/messages/${messageId}`, { method: 'DELETE' })
      setMessages(prev => prev.filter(m => m.id !== messageId))
      if (selectedMessage?.id === messageId) setSelectedMessage(null)
    } catch (err) {
      console.error('Failed to delete message:', err)
    }
  }, [emailAddress, selectedMessage])

  const sendTestEmail = useCallback(async () => {
    if (!emailAddress) return
    try {
      const res = await fetch(`${API_BASE}/email/send-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_address: emailAddress }),
      })
      if (res.ok) {
        await fetchMessages()
        return true
      }
    } catch (err) {
      console.error('Failed to send test email:', err)
    }
    return false
  }, [emailAddress, fetchMessages])

  const deleteEmail = useCallback(async () => {
    if (!emailAddress) return
    try {
      await fetch(`${API_BASE}/email/${emailAddress}`, { method: 'DELETE' })
    } catch (err) {
      // ignore
    }
    setEmailAddress(null)
    setEmailInfo(null)
    setMessages([])
    setSelectedMessage(null)
    setTimeRemaining(0)
  }, [emailAddress])

  // Polling for new messages
  useEffect(() => {
    if (!emailAddress) return
    pollingRef.current = setInterval(fetchMessages, 3000)
    return () => clearInterval(pollingRef.current)
  }, [emailAddress, fetchMessages])

  // Countdown timer
  useEffect(() => {
    if (timeRemaining <= 0) return
    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          clearInterval(interval)
          setEmailAddress(null)
          setEmailInfo(null)
          setMessages([])
          setSelectedMessage(null)
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [timeRemaining > 0])

  // WebSocket connection
  useEffect(() => {
    if (!emailAddress) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/${emailAddress}`

    try {
      const ws = new WebSocket(wsUrl)
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'new_message') {
          setMessages(prev => [data.message, ...prev])
        }
      }
      ws.onerror = () => {} // fallback to polling
      wsRef.current = ws
    } catch {
      // WebSocket not available, polling will handle it
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [emailAddress])

  const value = {
    emailAddress,
    emailInfo,
    messages,
    selectedMessage,
    loading,
    timeRemaining,
    generateEmail,
    fetchMessages,
    readMessage,
    deleteMessage,
    sendTestEmail,
    deleteEmail,
    setSelectedMessage,
    unreadCount: messages.filter(m => !m.is_read).length,
  }

  return (
    <EmailContext.Provider value={value}>
      {children}
    </EmailContext.Provider>
  )
}

export function useEmail() {
  const context = useContext(EmailContext)
  if (!context) throw new Error('useEmail must be used within EmailProvider')
  return context
}
