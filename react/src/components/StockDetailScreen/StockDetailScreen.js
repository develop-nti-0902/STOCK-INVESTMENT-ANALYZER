import React from 'react'
import { ArrowLeft, TrendingUp, TrendingDown, Activity, Shield, DollarSign } from 'lucide-react'
import ScoreCircle from '../common/ScoreCircle'
import styles from './StockDetailScreen.module.css'

export default function StockDetailScreen({ selectedStock, setCurrentScreen }) {
  if (!selectedStock) {
    return (
      <div className={styles.container}>
        <div className={styles.emptyState}>
          <p className={styles.noStock}>銘柄が選択されていません。</p>
          <button onClick={() => setCurrentScreen('list')} className={styles.backButton}>
            <ArrowLeft size={18} />
            一覧に戻る
          </button>
        </div>
      </div>
    )
  }

  // データの存在チェックとデフォルト値
  const stock = {
    code: selectedStock.code || '',
    name: selectedStock.name || '',
    sector: selectedStock.sector || '',
    price: selectedStock.price || 0,
    change: selectedStock.change || 0,
    fundamental: selectedStock.fundamental || 0,
    supply: selectedStock.supply || 0,
    risk: selectedStock.risk || 0,
    overall: selectedStock.overall || 0,
    per: selectedStock.per || 0,
    pbr: selectedStock.pbr || 0,
    roe: selectedStock.roe || 0,
    dividendYield: selectedStock.dividendYield || 0,
    volumeRatio: selectedStock.volumeRatio || 0,
    marginRatio: selectedStock.marginRatio || 0,
    foreignOwnership: selectedStock.foreignOwnership || 0,
    volatility: selectedStock.volatility || 0,
    beta: selectedStock.beta || 1.0,
    valuation: selectedStock.valuation || {
      label: '不明',
      color: '#6b7280',
      score: 50,
      reasons: ['データが不足しています']
    }
  }

  return (
    <div className={styles.container}>
      {/* ヘッダー */}
      <div className={styles.header}>
        <button onClick={() => setCurrentScreen('list')} className={styles.backButton}>
          <ArrowLeft size={18} />
          一覧に戻る
        </button>
      </div>

      {/* 銘柄タイトル */}
      <div className={styles.titleSection}>
        <div>
          <h2 className={styles.title}>{stock.code} {stock.name}</h2>
          <div className={styles.sector}>{stock.sector}</div>
        </div>
        <div className={styles.priceSection}>
          <div className={styles.currentPrice}>¥{stock.price.toLocaleString()}</div>
          <div className={stock.change > 0 ? styles.priceChangePositive : styles.priceChangeNegative}>
            {stock.change > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {stock.change > 0 ? '+' : ''}{stock.change}%
          </div>
        </div>
      </div>

      {/* 割安度セクション */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <DollarSign size={20} />
          割安度分析
        </h3>
        <div className={styles.valuationCard}>
          <div 
            className={styles.valuationBadge}
            style={{ 
              backgroundColor: `${stock.valuation.color}20`,
              color: stock.valuation.color,
              border: `2px solid ${stock.valuation.color}`
            }}
          >
            <div className={styles.valuationLabel}>{stock.valuation.label}</div>
            <div className={styles.valuationScore}>スコア: {stock.valuation.score}/100</div>
          </div>
          <div className={styles.valuationReasons}>
            <div className={styles.reasonsTitle}>判定理由:</div>
            <ul className={styles.reasonsList}>
              {stock.valuation.reasons.map((reason, index) => (
                <li key={index}>{reason}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* スコアサマリー */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <Activity size={20} />
          総合スコア
        </h3>
        <div className={styles.scoreGrid}>
          <div className={styles.scoreCard}>
            <div className={styles.scoreLabel}>ファンダメンタル</div>
            <ScoreCircle score={stock.fundamental} size="lg" />
            <div className={styles.scoreValue}>{stock.fundamental}</div>
          </div>
          <div className={styles.scoreCard}>
            <div className={styles.scoreLabel}>需給</div>
            <ScoreCircle score={stock.supply} size="lg" />
            <div className={styles.scoreValue}>{stock.supply}</div>
          </div>
          <div className={styles.scoreCard}>
            <div className={styles.scoreLabel}>リスク</div>
            <ScoreCircle score={stock.risk} size="lg" />
            <div className={styles.scoreValue}>{stock.risk}</div>
          </div>
          <div className={styles.scoreCard}>
            <div className={styles.scoreLabel}>総合</div>
            <ScoreCircle score={stock.overall} size="lg" />
            <div className={styles.scoreValue}>{stock.overall}</div>
          </div>
        </div>
      </div>

      {/* ファンダメンタル分析 */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <TrendingUp size={20} />
          ファンダメンタル分析
        </h3>
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>PER (株価収益率)</div>
            <div className={styles.metricValue}>{stock.per}倍</div>
            <div className={styles.metricDescription}>
              {stock.per < 15 ? '✓ 割安水準' : stock.per < 25 ? '→ 平均的' : '⚠ 割高水準'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>PBR (株価純資産倍率)</div>
            <div className={styles.metricValue}>{stock.pbr}倍</div>
            <div className={styles.metricDescription}>
              {stock.pbr < 1.0 ? '✓ 純資産割れ' : stock.pbr < 2.0 ? '✓ 低水準' : '→ 平均的'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>ROE (自己資本利益率)</div>
            <div className={styles.metricValue}>{stock.roe}%</div>
            <div className={styles.metricDescription}>
              {stock.roe > 15 ? '✓ 高収益性' : stock.roe > 10 ? '→ 平均的' : '⚠ 低収益性'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>配当利回り</div>
            <div className={styles.metricValue}>{stock.dividendYield}%</div>
            <div className={styles.metricDescription}>
              {stock.dividendYield > 4.0 ? '✓ 高配当' : stock.dividendYield > 2.5 ? '→ 平均的' : '⚠ 低配当'}
            </div>
          </div>
        </div>
      </div>

      {/* 需給分析 */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <Activity size={20} />
          需給分析
        </h3>
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>出来高比率</div>
            <div className={styles.metricValue}>{stock.volumeRatio}%</div>
            <div className={styles.metricDescription}>
              {stock.volumeRatio > 150 ? '✓ 活発な取引' : stock.volumeRatio > 100 ? '→ 平均的' : '⚠ 閑散'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>信用倍率</div>
            <div className={styles.metricValue}>{stock.marginRatio}倍</div>
            <div className={styles.metricDescription}>
              {stock.marginRatio < 1.0 ? '✓ 買い優勢' : stock.marginRatio < 3.0 ? '→ 均衡' : '⚠ 売り優勢'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>外国人保有比率</div>
            <div className={styles.metricValue}>{stock.foreignOwnership}%</div>
            <div className={styles.metricDescription}>
              {Math.abs(stock.foreignOwnership - 30) < 10 ? '✓ 理想的' : '→ 平均的'}
            </div>
          </div>
        </div>
      </div>

      {/* リスク分析 */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>
          <Shield size={20} />
          リスク分析
        </h3>
        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>ボラティリティ</div>
            <div className={styles.metricValue}>{stock.volatility}%</div>
            <div className={styles.metricDescription}>
              {stock.volatility < 15 ? '✓ 低リスク' : stock.volatility < 25 ? '→ 中リスク' : '⚠ 高リスク'}
            </div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricLabel}>ベータ値</div>
            <div className={styles.metricValue}>{stock.beta}</div>
            <div className={styles.metricDescription}>
              {Math.abs(stock.beta - 1.0) < 0.2 ? '✓ 市場連動' : stock.beta < 1.0 ? '✓ ディフェンシブ' : '⚠ 高ボラ'}
            </div>
          </div>
        </div>
      </div>

      {/* 投資判断サマリー */}
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>投資判断サマリー</h3>
        <div className={styles.summaryCard}>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>総合評価:</span>
            <span className={styles.summaryValue}>
              {stock.overall >= 80 ? '◎ 強く推奨' : 
               stock.overall >= 60 ? '○ 推奨' : 
               stock.overall >= 40 ? '△ 中立' : '× 非推奨'}
            </span>
          </div>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>割安度:</span>
            <span className={styles.summaryValue} style={{ color: stock.valuation.color }}>
              {stock.valuation.label}
            </span>
          </div>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>投資スタイル:</span>
            <span className={styles.summaryValue}>
              {stock.dividendYield > 4.0 ? '配当重視' : 
               stock.roe > 15 ? '成長重視' : 
               stock.pbr < 1.0 ? 'バリュー' : 'バランス'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}