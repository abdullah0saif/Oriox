import { useEffect, useRef } from 'react'

const ORBS = [
  { x: 20, y: 20, size: 600, color: 'rgba(99, 102, 241, 0.08)', speed: 0.0003 },
  { x: 70, y: 60, size: 500, color: 'rgba(167, 139, 250, 0.06)', speed: 0.0005 },
  { x: 50, y: 80, size: 700, color: 'rgba(34, 211, 238, 0.05)', speed: 0.0004 },
  { x: 80, y: 30, size: 400, color: 'rgba(244, 114, 182, 0.04)', speed: 0.0006 },
]

export default function AnimatedBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animationId
    let time = 0

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const draw = () => {
      time += 1
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      ORBS.forEach((orb) => {
        const x = canvas.width * (orb.x / 100) + Math.sin(time * orb.speed) * 100
        const y = canvas.height * (orb.y / 100) + Math.cos(time * orb.speed * 1.3) * 80
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, orb.size)
        gradient.addColorStop(0, orb.color)
        gradient.addColorStop(1, 'transparent')
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, canvas.width, canvas.height)
      })

      animationId = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <>
      <canvas
        ref={canvasRef}
        className="fixed inset-0 pointer-events-none"
        style={{ zIndex: 0 }}
      />
      <div className="fixed inset-0 pointer-events-none" style={{ zIndex: 0 }}>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-to-b from-accent-blue/5 to-transparent rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[400px] bg-gradient-to-tl from-accent-purple/5 to-transparent rounded-full blur-3xl" />
      </div>
    </>
  )
}
