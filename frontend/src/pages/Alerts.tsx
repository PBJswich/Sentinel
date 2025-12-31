import { useState, useEffect } from 'react'
import { api, Alert } from '../api/client'
import './Alerts.css'

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showActiveOnly, setShowActiveOnly] = useState(false)

  useEffect(() => {
    loadAlerts()
  }, [])

  const loadAlerts = async () => {
    setLoading(true)
    setError(null)
    try {
      const allData = await api.alerts.getAll()
      setAlerts(allData.alerts)
      // Active alerts are just enabled alerts
      setActiveAlerts(allData.alerts.filter((a) => a.enabled))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async (alert: Alert) => {
    try {
      await api.alerts.update(alert.alert_id, {
        enabled: !alert.enabled,
      })
      loadAlerts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update alert')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this alert?')) return

    try {
      await api.alerts.delete(id)
      loadAlerts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete alert')
    }
  }

  const getAlertTypeLabel = (type: string) => {
    return type
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const displayedAlerts = showActiveOnly ? activeAlerts : alerts

  if (loading) {
    return <div className="loading">Loading alerts...</div>
  }

  if (error) {
    return <div className="error">Error: {error}</div>
  }

  return (
    <div className="alerts-page">
      <div className="page-header">
        <h1>Alerts</h1>
        <p className="subtitle">Monitor signal changes and conditions</p>
        <div className="header-actions">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={showActiveOnly}
              onChange={(e) => setShowActiveOnly(e.target.checked)}
            />
            Show active only
          </label>
        </div>
      </div>

      <div className="alerts-stats">
        <div className="stat-card">
          <div className="stat-label">Total Alerts</div>
          <div className="stat-value">{alerts.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Active Alerts</div>
          <div className="stat-value">{activeAlerts.length}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Enabled</div>
          <div className="stat-value">
            {alerts.filter((a) => a.enabled).length}
          </div>
        </div>
      </div>

      {displayedAlerts.length === 0 ? (
        <div className="empty-state">
          <p>
            {showActiveOnly
              ? 'No active alerts at this time.'
              : 'No alerts configured. Create alerts to monitor signal changes.'}
          </p>
        </div>
      ) : (
        <div className="alerts-list">
          {displayedAlerts.map((alert) => (
            <div
              key={alert.alert_id}
              className={`alert-card ${alert.enabled ? 'enabled' : 'disabled'}`}
            >
              <div className="alert-header">
                <div>
                  <h3>{alert.name}</h3>
                  <span className="alert-type">
                    {getAlertTypeLabel(alert.alert_type)}
                  </span>
                </div>
                <div className="alert-actions">
                  <button
                    className={`toggle-btn ${alert.enabled ? 'enabled' : 'disabled'}`}
                    onClick={() => handleToggle(alert)}
                  >
                    {alert.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    className="btn-danger"
                    onClick={() => handleDelete(alert.alert_id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <p className="alert-description">{alert.description}</p>
              {alert.last_triggered && (
                <div className="alert-meta">
                  Last triggered: {new Date(alert.last_triggered).toLocaleString()}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

