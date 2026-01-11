import React from 'react';
import { TrendingUp, AlertTriangle, Star } from 'lucide-react';
import { PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ScoreCircle from '../common/ScoreCircle';
import styles from './DashboardScreen.module.css';

const OverallScoreBadge = ({ score }) => {
  const badgeClass = {
    '◎': styles.badgeExcellent,
    '○': styles.badgeGood,
    '△': styles.badgeFair,
    '×': styles.badgePoor
  }[score];

  return (
    <span className={`${styles.overallBadge} ${badgeClass}`}>
      {score}
    </span>
  );
};

export default function DashboardScreen({ portfolioData, favorites, toggleFavorite }) {
  const sectorData = [
    { name: '輸送用機器', value: 30, color: '#3b82f6' },
    { name: '情報・通信業', value: 25, color: '#10b981' },
    { name: '電気機器', value: 30, color: '#f59e0b' },
    { name: '化学', value: 15, color: '#8b5cf6' }
  ];

  const radarData = [
    { metric: '成長性', value: 85 },
    { metric: '収益性', value: 78 },
    { metric: '安定性', value: 82 },
    { metric: '需給', value: 72 },
    { metric: '流動性', value: 88 }
  ];

  const alerts = [
    { type: 'warning', message: 'トヨタ自動車：決算発表まであと3日', priority: 'high' },
    { type: 'danger', message: 'ソフトバンクG：貸株金利が2.5%→4.2%に上昇', priority: 'high' },
    { type: 'info', message: 'キーエンス：空売り残が前週比+15%', priority: 'medium' }
  ];

  const recentNews = [
    { date: '2024/12/28', title: 'トヨタ、EV新戦略発表へ', sentiment: 'positive' },
    { date: '2024/12/27', title: 'ソフトバンクG、AI投資拡大', sentiment: 'positive' },
    { date: '2024/12/26', title: '半導体関連に注目集まる', sentiment: 'neutral' }
  ];

  return (
    <div className={styles.dashboard}>
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>総評価額</div>
          <div className={styles.statValue}>¥{portfolioData.totalValue.toLocaleString()}</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>含み損益</div>
          <div className={`${styles.statValue} ${styles.positive}`}>
            <TrendingUp size={28} />
            +¥{portfolioData.unrealizedPL.toLocaleString()}
          </div>
          <div className={styles.statPercent}>+{portfolioData.unrealizedPLPercent}%</div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>年間実現損益</div>
          <div className={`${styles.statValue} ${styles.info}`}>
            +¥{portfolioData.realizedPLYear.toLocaleString()}
          </div>
        </div>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>総合スコア</div>
          <div className={styles.badgeContainer}>
            <OverallScoreBadge score={portfolioData.overallScore} />
          </div>
        </div>
      </div>

      <div className={styles.mainGrid}>
        <div className={styles.holdingsCard}>
          <h3 className={styles.cardTitle}>保有銘柄 TOP5 リスク</h3>
          <div className={styles.holdingsList}>
            {portfolioData.holdings.map((stock) => (
              <div key={stock.code} className={styles.holdingItem}>
                <div className={styles.holdingInfo}>
                  <button onClick={() => toggleFavorite(stock.code)} className={styles.favoriteBtn}>
                    <Star size={18} className={favorites.includes(stock.code) ? styles.favoriteActive : styles.favoriteInactive} />
                  </button>
                  <div>
                    <div className={styles.stockName}>{stock.code} {stock.name}</div>
                    <div className={styles.sector}>{stock.sector}</div>
                  </div>
                </div>
                <div className={styles.holdingStats}>
                  <div className={styles.priceInfo}>
                    <div className={styles.price}>¥{stock.currentPrice.toLocaleString()}</div>
                    <div className={stock.plPercent > 0 ? styles.plPositive : styles.plNegative}>
                      {stock.plPercent > 0 ? '+' : ''}{stock.plPercent}%
                    </div>
                  </div>
                  <div className={styles.scores}>
                    <ScoreCircle score={stock.fundamental} size="sm" />
                    <ScoreCircle score={stock.supply} size="sm" />
                    <ScoreCircle score={stock.risk} size="sm" />
                  </div>
                  <ScoreCircle score={stock.overall} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.sectorCard}>
          <h3 className={styles.cardTitle}>セクター別配分</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={sectorData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>
                {sectorData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className={styles.sectorLegend}>
            {sectorData.map((sector) => (
              <div key={sector.name} className={styles.legendItem}>
                <div className={styles.legendLabel}>
                  <div className={styles.legendColor} style={{ backgroundColor: sector.color }}></div>
                  <span>{sector.name}</span>
                </div>
                <span className={styles.legendValue}>{sector.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className={styles.bottomGrid}>
        <div className={styles.radarCard}>
          <h3 className={styles.cardTitle}>ポートフォリオ分析</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" />
              <PolarRadiusAxis angle={90} domain={[0, 100]} />
              <Radar name="スコア" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className={styles.sideColumn}>
          <div className={styles.alertsCard}>
            <h3 className={styles.cardTitle}>
              <AlertTriangle className={styles.alertIcon} />
              注意アラート
            </h3>
            <div className={styles.alertsList}>
              {alerts.map((alert, idx) => (
                <div key={idx} className={`${styles.alertItem} ${alert.priority === 'high' ? styles.alertHigh : styles.alertMedium}`}>
                  <div className={styles.alertMessage}>{alert.message}</div>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.newsCard}>
            <h3 className={styles.cardTitle}>最近のニュース</h3>
            <div className={styles.newsList}>
              {recentNews.map((news, idx) => (
                <div key={idx} className={styles.newsItem}>
                  <div className={styles.newsDate}>{news.date}</div>
                  <div className={styles.newsTitle}>{news.title}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}