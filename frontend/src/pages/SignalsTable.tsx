import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api, Signal, SignalsResponse } from '../api/client'
import './SignalsTable.css'

export default function SignalsTable() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    market: '',
    category: '',
    direction: '',
    confidence: '',
    search: '',
    sort_by: 'date',
  })
  const [markets, setMarkets] = useState<string[]>([])

  useEffect(() => {
    loadMarkets()
  }, [])

  useEffect(() => {
    loadSignals()
  }, [filters])

  const loadMarkets = async () => {
    try {
      const data = await api.markets.getAll()
      setMarkets(data.markets.map((m) => m.market))
    } catch (err) {
      console.error('Failed to load markets:', err)
      // Don't set error state for markets, just log it
    }
  }

  const loadSignals = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.signals.getAll({
        market: filters.market || undefined,
        category: filters.category || undefined,
        direction: filters.direction || undefined,
        confidence: filters.confidence || undefined,
        search: filters.search || undefined,
        sort_by: filters.sort_by || undefined,
      })
      setSignals(data?.signals || [])
    } catch (err) {
      console.error('Error loading signals:', err)
      setError(err instanceof Error ? err.message : 'Failed to load signals')
      setSignals([]) // Set empty array on error to prevent crashes
    } finally {
      setLoading(false)
    }
  }

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const getDirectionClass = (direction: string) => {
    switch (direction) {
      case 'Bullish':
        return 'direction-bullish'
      case 'Bearish':
        return 'direction-bearish'
      default:
        return 'direction-neutral'
    }
  }

  const getConfidenceClass = (confidence: string) => {
    switch (confidence) {
      case 'High':
        return 'confidence-high'
      case 'Medium':
        return 'confidence-medium'
      default:
        return 'confidence-low'
    }
  }

  if (loading && signals.length === 0) {
    return (
      <div className="signals-table-page">
        <div className="loading">Loading signals...</div>
      </div>
    )
  }

  if (error && signals.length === 0) {
    return (
      <div className="signals-table-page">
        <div className="error">
          <h2>Error loading signals</h2>
          <p>{error}</p>
          <p style={{ marginTop: '1rem', fontSize: '0.875rem', color: '#64748b' }}>
            Make sure the backend API is running on http://localhost:8000
          </p>
          <button
            onClick={() => {
              setError(null)
              loadSignals()
            }}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="signals-table-page">
      <div className="page-header">
        <h1>Signals</h1>
        <p className="subtitle">Cross-commodity trading signals across all markets</p>
      </div>

      <div className="filters">
        <div className="filter-group">
          <label>Search</label>
          <input
            type="text"
            placeholder="Search signals..."
            value={filters.search}
            onChange={(e) => handleFilterChange('search', e.target.value)}
          />
        </div>
        <div className="filter-group">
          <label>Market</label>
          <select
            value={filters.market}
            onChange={(e) => handleFilterChange('market', e.target.value)}
          >
            <option value="">All Markets</option>
            {markets.map((market) => (
              <option key={market} value={market}>
                {market}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <label>Category</label>
          <select
            value={filters.category}
            onChange={(e) => handleFilterChange('category', e.target.value)}
          >
            <option value="">All Categories</option>
            <option value="Technical">Technical</option>
            <option value="Macro">Macro</option>
            <option value="Fundamental">Fundamental</option>
            <option value="Sentiment">Sentiment</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Direction</label>
          <select
            value={filters.direction}
            onChange={(e) => handleFilterChange('direction', e.target.value)}
          >
            <option value="">All Directions</option>
            <option value="Bullish">Bullish</option>
            <option value="Bearish">Bearish</option>
            <option value="Neutral">Neutral</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Confidence</label>
          <select
            value={filters.confidence}
            onChange={(e) => handleFilterChange('confidence', e.target.value)}
          >
            <option value="">All Confidence</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
        <div className="filter-group">
          <label>Sort By</label>
          <select
            value={filters.sort_by}
            onChange={(e) => handleFilterChange('sort_by', e.target.value)}
          >
            <option value="date">Date</option>
            <option value="confidence">Confidence</option>
            <option value="market">Market</option>
            <option value="age">Age</option>
          </select>
        </div>
      </div>

      <div className="signals-count">
        Showing {signals.length} signal{signals.length !== 1 ? 's' : ''}
      </div>

      <div className="table-container">
        <table className="signals-table">
          <thead>
            <tr>
              <th>Market</th>
              <th>Category</th>
              <th>Signal</th>
              <th>Direction</th>
              <th>Confidence</th>
              <th>Score</th>
              <th>Updated</th>
              <th>Explanation</th>
            </tr>
          </thead>
          <tbody>
            {signals.length === 0 ? (
              <tr>
                <td colSpan={8} className="no-data">
                  No signals found matching your filters.
                </td>
              </tr>
            ) : (
              signals.map((signal) => (
                <tr key={signal.signal_id}>
                  <td>
                    <Link to={`/market/${encodeURIComponent(signal.market)}`}>
                      {signal.market}
                    </Link>
                  </td>
                  <td>{signal.category}</td>
                  <td>{signal.name}</td>
                  <td>
                    <span className={`direction-badge ${getDirectionClass(signal.direction)}`}>
                      {signal.direction}
                    </span>
                  </td>
                  <td>
                    <span className={`confidence-badge ${getConfidenceClass(signal.confidence)}`}>
                      {signal.confidence}
                    </span>
                  </td>
                  <td>
                    {signal.score !== undefined && signal.score !== null ? (
                      <span className={`score ${signal.score >= 0 ? 'score-positive' : 'score-negative'}`}>
                        {signal.score > 0 ? '+' : ''}{Number(signal.score).toFixed(2)}
                      </span>
                    ) : (
                      <span className="score-na">—</span>
                    )}
                  </td>
                  <td>{new Date(signal.last_updated).toLocaleDateString()}</td>
                  <td className="explanation">{signal.explanation}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

