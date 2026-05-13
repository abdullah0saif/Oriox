import React from 'react';

const styles = {
  container: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: 12,
    marginBottom: 24,
  },
  card: {
    background: '#12121f',
    borderRadius: 10,
    padding: '16px 20px',
    border: '1px solid #1a1a2e',
  },
  label: {
    fontSize: 11,
    color: '#666',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: 6,
  },
  value: {
    fontSize: 20,
    fontWeight: 700,
  },
  sub: {
    fontSize: 12,
    color: '#888',
    marginTop: 4,
  },
};

function getTrendColor(trend) {
  if (trend === 'bullish') return '#00e676';
  if (trend === 'bearish') return '#ff1744';
  return '#ffab00';
}

function getFgColor(index) {
  if (!index) return '#888';
  if (index <= 25) return '#ff1744';
  if (index <= 45) return '#ff6d00';
  if (index <= 55) return '#ffab00';
  if (index <= 75) return '#76ff03';
  return '#00e676';
}

function getFgLabel(index) {
  if (!index) return '';
  if (index <= 25) return 'Extreme Fear';
  if (index <= 45) return 'Fear';
  if (index <= 55) return 'Neutral';
  if (index <= 75) return 'Greed';
  return 'Extreme Greed';
}

export default function MarketOverview({ data }) {
  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.label}>BTC Price</div>
        <div style={styles.value}>${data.btc_price?.toLocaleString()}</div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>BTC Dominance</div>
        <div style={styles.value}>{data.btc_dominance?.toFixed(1)}%</div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>Fear & Greed</div>
        <div style={{ ...styles.value, color: getFgColor(data.fear_greed_index) }}>
          {data.fear_greed_index ?? 'N/A'}
        </div>
        <div style={styles.sub}>{getFgLabel(data.fear_greed_index)}</div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>Market Trend</div>
        <div style={{ ...styles.value, color: getTrendColor(data.market_trend) }}>
          {data.market_trend?.toUpperCase()}
        </div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>Market Breadth</div>
        <div style={styles.value}>{data.breadth_bullish_pct?.toFixed(0)}%</div>
        <div style={styles.sub}>above 20 EMA</div>
      </div>

      <div style={styles.card}>
        <div style={styles.label}>Scan Results</div>
        <div style={styles.value}>
          {data.setups_approved}/{data.setups_found}
        </div>
        <div style={styles.sub}>
          {data.symbols_scanned} symbols in {data.scan_duration_seconds?.toFixed(1)}s
        </div>
      </div>
    </div>
  );
}
