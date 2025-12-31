import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from './components/ErrorBoundary'
import Layout from './components/Layout'
import SignalsTable from './pages/SignalsTable'
import MarketDetail from './pages/MarketDetail'
import Watchlists from './pages/Watchlists'
import Alerts from './pages/Alerts'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<SignalsTable />} />
            <Route path="/market/:market" element={<MarketDetail />} />
            <Route path="/watchlists" element={<Watchlists />} />
            <Route path="/alerts" element={<Alerts />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

