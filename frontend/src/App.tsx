import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import { AdminPage } from '@/pages/AdminPage'
import { ChatPage } from '@/pages/ChatPage'
import { cn } from '@/lib/utils'

function NavItem({ to, children }: { to: string; children: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'rounded px-3 py-1 text-sm',
          isActive
            ? 'bg-neutral-900 text-white'
            : 'text-neutral-600 hover:bg-neutral-100',
        )
      }
    >
      {children}
    </NavLink>
  )
}

export default function App() {
  return (
    <div className="flex h-full flex-col">
      <nav className="flex gap-2 border-b border-neutral-200 px-4 py-2">
        <NavItem to="/chat">Чат</NavItem>
        <NavItem to="/admin">Админ</NavItem>
      </nav>

      <main className="flex min-h-0 flex-1 flex-col">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>
    </div>
  )
}
