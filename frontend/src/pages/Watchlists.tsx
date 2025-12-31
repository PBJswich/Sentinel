import { useState, useEffect } from 'react'
import { api, Watchlist, Signal } from '../api/client'
import './Watchlists.css'

export default function Watchlists() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newWatchlistName, setNewWatchlistName] = useState('')

  useEffect(() => {
    loadWatchlists()
  }, [])

  const loadWatchlists = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.watchlists.getAll()
      setWatchlists(data.watchlists)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load watchlists')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newWatchlistName.trim()) return

    try {
      await api.watchlists.create({
        name: newWatchlistName,
        signal_ids: [],
        market_ids: [],
      })
      setNewWatchlistName('')
      setShowCreateForm(false)
      loadWatchlists()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to create watchlist')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this watchlist?')) return

    try {
      await api.watchlists.delete(id)
      loadWatchlists()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete watchlist')
    }
  }

  if (loading) {
    return <div className="loading">Loading watchlists...</div>
  }

  if (error) {
    return <div className="error">Error: {error}</div>
  }

  return (
    <div className="watchlists-page">
      <div className="page-header">
        <h1>Watchlists</h1>
        <p className="subtitle">Manage your signal and market watchlists</p>
        <button
          className="btn-primary"
          onClick={() => setShowCreateForm(!showCreateForm)}
        >
          {showCreateForm ? 'Cancel' : '+ New Watchlist'}
        </button>
      </div>

      {showCreateForm && (
        <div className="create-form">
          <form onSubmit={handleCreate}>
            <input
              type="text"
              placeholder="Watchlist name"
              value={newWatchlistName}
              onChange={(e) => setNewWatchlistName(e.target.value)}
              autoFocus
            />
            <button type="submit" className="btn-primary">
              Create
            </button>
          </form>
        </div>
      )}

      {watchlists.length === 0 ? (
        <div className="empty-state">
          <p>No watchlists yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="watchlists-grid">
          {watchlists.map((watchlist) => (
            <WatchlistCard
              key={watchlist.watchlist_id}
              watchlist={watchlist}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function WatchlistCard({
  watchlist,
  onDelete,
}: {
  watchlist: Watchlist
  onDelete: (id: string) => void
}) {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSignals()
  }, [watchlist.watchlist_id])

  const loadSignals = async () => {
    setLoading(true)
    try {
      const data = await api.watchlists.getSignals(watchlist.watchlist_id)
      setSignals(data.signals)
    } catch (err) {
      console.error('Failed to load signals:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="watchlist-card">
      <div className="watchlist-header">
        <h3>{watchlist.name}</h3>
        <button
          className="btn-danger"
          onClick={() => onDelete(watchlist.watchlist_id)}
        >
          Delete
        </button>
      </div>
      <div className="watchlist-stats">
        <div className="stat">
          <span className="stat-label">Signals</span>
          <span className="stat-value">{watchlist.signal_ids.length}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Markets</span>
          <span className="stat-value">{watchlist.market_ids.length}</span>
        </div>
      </div>
      {loading ? (
        <div className="loading-small">Loading signals...</div>
      ) : signals.length > 0 ? (
        <div className="watchlist-signals">
          {signals.slice(0, 5).map((signal) => (
            <div key={signal.signal_id} className="signal-item">
              <span className="signal-name">{signal.name}</span>
              <span className={`signal-direction ${signal.direction.toLowerCase()}`}>
                {signal.direction}
              </span>
            </div>
          ))}
          {signals.length > 5 && (
            <div className="more-signals">+{signals.length - 5} more</div>
          )}
        </div>
      ) : (
        <div className="no-signals">No signals in this watchlist</div>
      )}
    </div>
  )
}

