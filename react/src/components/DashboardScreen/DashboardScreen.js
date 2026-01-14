import React from 'react';
import { TrendingUp, Star } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import styles from './DashboardScreen.module.css';

export default function DashboardScreen({ portfolioData, stockList, favorites, toggleFavorite, setSelectedStock, setCurrentScreen }) {
  // セクター別配分データの計算
  const sectorData = [
    { name: '輸送用機器', value: 30, color: '#3b82f6' },
    { name: '情報・通信業', value: 25, color: '#10b981' },
    { name: '電気機器', value: 30, color: '#f59e0b' },
    { name: '化学', value: 15, color: '#8b5cf6' }
  ];

  return (
    <div className={styles.dashboard}>
      {/* 統計カード */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statLabel}>総評価額</div>
          <div className={styles.statValue}>¥{portfolioData.totalValue.toLocaleString()}</div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statLabel}>含み損益</div>
          <div className={`${styles.statValue} ${portfolioData.unrealizedPL > 0 ? styles.positive : styles.negative}`}>
            <TrendingUp size={28} />
            {portfolioData.unrealizedPL > 0 ? '+' : ''}¥{portfolioData.unrealizedPL.toLocaleString()}
          </div>
          <div className={`${styles.statPercent} ${portfolioData.unrealizedPLPercent > 0 ? styles.positive : styles.negative}`}>
            {portfolioData.unrealizedPLPercent > 0 ? '+' : ''}{portfolioData.unrealizedPLPercent}%
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statLabel}>年間実現損益</div>
          <div className={`${styles.statValue} ${styles.info}`}>
            +¥{portfolioData.realizedPLYear.toLocaleString()}
          </div>
        </div>
      </div>

      {/* メインコンテンツ */}
      <div className={styles.mainGrid}>
        {/* 保有銘柄一覧 */}
        <div className={styles.holdingsCard}>
          <h3 className={styles.cardTitle}>保有銘柄一覧</h3>
          <div className={styles.holdingsList}>
            {portfolioData.holdings.map((stock) => (
              <div
                key={stock.code}
                className={styles.holdingItem}
                onClick={() => {
                  setSelectedStock(stockList.find(s => s.code === stock.code));
                  setCurrentScreen('detail', 'dashboard');
                }}
              >
                <div className={styles.holdingInfo}>
                  <div>
                    <div className={styles.stockName}>{stock.code} {stock.name}</div>
                    <div className={styles.sector}>{stock.sector}</div>
                  </div>
                </div>
                <div className={styles.holdingStats}>
                  <div className={styles.priceColumn}>
                    <div className={styles.priceRow}>
                      <span className={styles.priceLabel}>現在</span>
                      <span className={styles.price}>¥{stock.currentPrice?.toLocaleString() || '-'}</span>
                    </div>
                    <div className={styles.priceRow}>
                      <span className={styles.priceLabel}>購入</span>
                      <span className={styles.priceSecondary}>¥{stock.purchasePrice?.toLocaleString() || '-'}</span>
                    </div>
                  </div>
                  <div className={styles.plColumn}>
                    <div className={(stock.pl || 0) > 0 ? styles.plPositive : styles.plNegative}>
                      {stock.pl ? `${stock.pl > 0 ? '+' : ''}¥${stock.pl.toLocaleString()}` : '-'}
                    </div>
                    <div className={(stock.plPercent || 0) > 0 ? styles.plPositive : styles.plNegative}>
                      {stock.plPercent ? `${stock.plPercent > 0 ? '+' : ''}${stock.plPercent}%` : '-'}
                    </div>
                  </div>
                  <div className={styles.lineColumn}>
                    <div className={styles.lineRow}>
                      <span className={styles.lineLabel}>利確</span>
                      <span className={styles.lineValue}>¥{stock.takeProfitLine?.toLocaleString() || '-'}</span>
                    </div>
                    <div className={styles.lineRow}>
                      <span className={styles.lineLabel}>損切</span>
                      <span className={styles.lineValue}>¥{stock.stopLossLine?.toLocaleString() || '-'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* セクター別配分 */}
        <div className={styles.sectorCard}>
          <h3 className={styles.cardTitle}>セクター別配分</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={sectorData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                dataKey="value"
                label={({ name, value }) => `${value}%`}
              >
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
    </div>
  );
}