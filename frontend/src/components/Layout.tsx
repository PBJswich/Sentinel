import { Link, useLocation } from 'react-router-dom'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="layout">
      <header className="header">
        <div className="header-content">
          <Link to="/" className="logo">
            <h1>Sentinel</h1>
            <span className="subtitle">Cross-Commodity Signal Dashboard</span>
          </Link>
          <nav className="nav">
            <Link
              to="/"
              className={isActive('/') ? 'nav-link active' : 'nav-link'}
            >
              Signals
            </Link>
            <Link
              to="/watchlists"
              className={isActive('/watchlists') ? 'nav-link active' : 'nav-link'}
            >
              Watchlists
            </Link>
            <Link
              to="/alerts"
              className={isActive('/alerts') ? 'nav-link active' : 'nav-link'}
            >
              Alerts
            </Link>
          </nav>
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  )
}
