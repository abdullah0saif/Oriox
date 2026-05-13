import React, { useState, useEffect, useCallback } from 'react';
import MarketOverview from './components/MarketOverview';
import SetupList from './components/SetupList';
import SetupDetail from './components/SetupDetail';

const styles = {
  container: {
    maxWidth: 1400,
    margin: '0 auto',
    padding: '20px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 24,
    borderBottom: '1px solid #1a1a2e',
    paddingBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    background: 'linear-gradient(135deg, #00d4ff, #7b2ff7)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    fontSize: 13,
    color: '#666',
    marginTop: 4,
  },
  scanBtn: {
    padding: '10px 24px',
    background: 'linear-gradient(135deg, #00d4ff, #7b2ff7)',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
  scanBtnDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 20,
  },
  status: {
    textAlign: 'center',
    padding: 40,
    color: '#666',
    fontSize: 14,
  },
  controls: {
    display: 'flex',
    gap: 12,
    alignItems: 'center',
  },
  select: {
    padding: '8px 12px',
    background: '#12121f',
    border: '1px solid #1a1a2e',
    borderRadius: 6,
    color: '#e0e0e0',
    fontSize: 13,
  },
};

export default function App() {
  const [scanData, setScanData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedSetup, setSelectedSetup] = useState(null);
  const [exchange, setExchange] = useState('binance');
  const [timeframe, setTimeframe] = useState('4h');

  const runScan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(
        `/api/setups/scan?exchange=${exchange}&timeframe=${timeframe}`
      );
      if (!resp.ok) throw new Error(`Scan failed: ${resp.status}`);
      const data = await resp.json();
      setScanData(data);
      setSelectedSetup(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [exchange, timeframe]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <div style={styles.title}>Oriox</div>
          <div style={styles.subtitle}>
            AI-Powered Crypto Setup Hunter — Confluence-Based Analysis
          </div>
        </div>
        <div style={styles.controls}>
          <select
            style={styles.select}
            value={exchange}
            onChange={(e) => setExchange(e.target.value)}
          >
            <option value="binance">Binance</option>
            <option value="bybit">Bybit</option>
            <option value="mexc">MEXC</option>
          </select>
          <select
            style={styles.select}
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
          >
            <option value="15m">15m</option>
            <option value="1h">1H</option>
            <option value="4h">4H</option>
            <option value="1d">1D</option>
          </select>
          <button
            style={{
              ...styles.scanBtn,
              ...(loading ? styles.scanBtnDisabled : {}),
            }}
            onClick={runScan}
            disabled={loading}
          >
            {loading ? 'Scanning...' : 'Scan Market'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ color: '#ff4444', padding: 12, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {scanData && <MarketOverview data={scanData} />}

      {loading && <div style={styles.status}>Scanning markets...</div>}

      {scanData && !loading && (
        <div style={styles.grid}>
          <SetupList
            signals={scanData.signals}
            onSelect={setSelectedSetup}
            selected={selectedSetup}
          />
          <SetupDetail setup={selectedSetup} />
        </div>
      )}

      {!scanData && !loading && (
        <div style={styles.status}>
          Click "Scan Market" to detect high-quality trade setups
        </div>
      )}
    </div>
  );
}
