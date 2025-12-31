import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, Signal, MarketSummary } from '../api/client'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts'
import './MarketDetail.css'

export default function MarketDetail() {
  const { market } = useParams<{ market: string }>()
  const [signals, setSignals] = useState<Signal[]>([])
  const [summary, setSummary] = useState<MarketSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (market) {
      loadData()
    }
  }, [market])

  const loadData = async () => {
    if (!market) return
    setLoading(true)
    setError(null)
    try {
      const [signalsData, summaryData] = await Promise.all([
        api.signals.getByMarket(market),
        api.markets.getSummary(market),
      ])
      setSignals(signalsData.signals)
      setSummary(summaryData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
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

  // Prepare chart data
  const directionData = summary
    ? [
        { name: 'Bullish', value: summary.direction_breakdown.bullish, fill: '#16a34a' },
        { name: 'Bearish', value: summary.direction_breakdown.bearish, fill: '#dc2626' },
        { name: 'Neutral', value: summary.direction_breakdown.neutral, fill: '#94a3b8' },
      ]
    : []

  const confidenceData = summary
    ? [
        { name: 'High', value: summary.confidence_breakdown.high, fill: '#2563eb' },
        { name: 'Medium', value: summary.confidence_breakdown.medium, fill: '#f59e0b' },
        { name: 'Low', value: summary.confidence_breakdown.low, fill: '#6b7280' },
      ]
    : []

  const pillarData = summary
    ? Object.entries(summary.pillar_breakdown).map(([name, value]) => ({
        name,
        value,
      }))
    : []

  // Score trend data (simplified - would need historical data for real trend)
  const scoreTrendData = signals
    .filter((s) => s.score !== undefined)
    .map((s) => ({
      name: s.name,
      score: s.score || 0,
    }))
    .slice(0, 10)

  if (loading) {
    return <div className="loading">Loading market data...</div>
  }

  if (error) {
    return <div className="error">Error: {error}</div>
  }

  if (!summary) {
    return <div className="error">Market not found</div>
  }

  return (
    <div className="market-detail-page">
      <div className="page-header">
        <Link to="/" className="back-link">
          ← Back to Signals
        </Link>
        <h1>{market}</h1>
        <p className="subtitle">Market signal summary and details</p>
      </div>

      <div className="summary-cards">
        <div className="summary-card">
          <div className="card-label">Total Signals</div>
          <div className="card-value">{summary.total_signals}</div>
        </div>
        <div className="summary-card">
          <div className="card-label">Conflicts</div>
          <div className="card-value">{summary.conflicts.length}</div>
        </div>
      </div>

      <div className="charts-section">
        <div className="chart-card">
          <h3>Direction Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={directionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Confidence Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={confidenceData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#2563eb" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {pillarData.length > 0 && (
          <div className="chart-card">
            <h3>Pillar Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={pillarData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#2563eb" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="signals-section">
        <h2>Signals</h2>
        <div className="table-container">
          <table className="signals-table">
            <thead>
              <tr>
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
                  <td colSpan={7} className="no-data">
                    No signals found for this market.
                  </td>
                </tr>
              ) : (
                signals.map((signal) => (
                  <tr key={signal.signal_id}>
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
    </div>
  )
}

