import React from 'react';

const styles = {
  container: {
    background: '#12121f',
    borderRadius: 10,
    border: '1px solid #1a1a2e',
    overflow: 'hidden',
  },
  header: {
    padding: '16px 20px',
    borderBottom: '1px solid #1a1a2e',
    fontSize: 14,
    fontWeight: 600,
    color: '#aaa',
  },
  list: {
    maxHeight: 600,
    overflowY: 'auto',
  },
  item: {
    padding: '14px 20px',
    borderBottom: '1px solid #0d0d18',
    cursor: 'pointer',
    transition: 'background 0.15s',
  },
  itemHover: {
    background: '#1a1a2e',
  },
  itemSelected: {
    background: '#1a1a35',
    borderLeft: '3px solid #7b2ff7',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  symbol: {
    fontSize: 15,
    fontWeight: 700,
  },
  badge: {
    fontSize: 11,
    padding: '3px 8px',
    borderRadius: 4,
    fontWeight: 600,
  },
  meta: {
    fontSize: 12,
    color: '#888',
    marginTop: 6,
  },
  scores: {
    display: 'flex',
    gap: 12,
    marginTop: 8,
    fontSize: 11,
  },
  scorePill: {
    padding: '2px 8px',
    borderRadius: 4,
    background: '#1a1a2e',
  },
  empty: {
    padding: 40,
    textAlign: 'center',
    color: '#555',
    fontSize: 14,
  },
};

function dirBadge(direction) {
  const isLong = direction === 'long';
  return {
    ...styles.badge,
    background: isLong ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 23, 68, 0.15)',
    color: isLong ? '#00e676' : '#ff1744',
  };
}

export default function SetupList({ signals, onSelect, selected }) {
  if (!signals || signals.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.header}>Detected Setups</div>
        <div style={styles.empty}>No setups meet the quality threshold</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        Detected Setups ({signals.length})
      </div>
      <div style={styles.list}>
        {signals.map((sig, idx) => (
          <div
            key={idx}
            style={{
              ...styles.item,
              ...(selected === sig ? styles.itemSelected : {}),
            }}
            onClick={() => onSelect(sig)}
            onMouseEnter={(e) =>
              selected !== sig && (e.currentTarget.style.background = '#1a1a2e')
            }
            onMouseLeave={(e) =>
              selected !== sig && (e.currentTarget.style.background = 'transparent')
            }
          >
            <div style={styles.row}>
              <span style={styles.symbol}>{sig.symbol}</span>
              <span style={dirBadge(sig.direction)}>
                {sig.direction.toUpperCase()}
              </span>
            </div>
            <div style={styles.meta}>
              {sig.setup_type.replace(/_/g, ' ')} | {sig.timeframe} |{' '}
              {sig.market_type.toUpperCase()} | R:R {sig.rr_ratio}
            </div>
            <div style={styles.scores}>
              <span style={styles.scorePill}>
                Score: {sig.final_score.toFixed(0)}
              </span>
              <span style={styles.scorePill}>
                Conf: {sig.confidence}%
              </span>
              <span style={styles.scorePill}>
                Quality: {sig.quality_score.toFixed(0)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
