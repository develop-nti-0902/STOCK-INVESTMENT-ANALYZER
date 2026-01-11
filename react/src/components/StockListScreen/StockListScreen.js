import React, { useState } from 'react';
import { Star, Download, ChevronRight } from 'lucide-react';
import ScoreCircle from '../common/ScoreCircle';
import styles from './StockListScreen.module.css';

export default function StockListScreen({ stockList, favorites, toggleFavorite, setSelectedStock, setCurrentScreen }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSector, setFilterSector] = useState('');
  const [sortBy, setSortBy] = useState('overall');
  const [sortDir, setSortDir] = useState('desc');

  const filteredStocks = stockList
    .filter(s => !searchTerm || s.name.includes(searchTerm) || s.code.includes(searchTerm))
    .filter(s => !filterSector || s.sector === filterSector)
    .sort((a, b) => {
      const mult = sortDir === 'asc' ? 1 : -1;
      return (a[sortBy] - b[sortBy]) * mult;
    });

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortDir('desc');
    }
  };

  const getSortLabel = () => {
    const labels = {
      code: '銘柄コード',
      price: '現在値',
      change: '変動率',
      fundamental: 'ファンダ',
      supply: '需給',
      risk: 'リスク',
      overall: '総合スコア'
    };
    return labels[sortBy];
  };

  return (
    <div className={styles.container}>
      <div className={styles.searchBar}>
        <input
          type="text"
          placeholder="銘柄名・コードで検索"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className={styles.searchInput}
        />
        <select
          value={filterSector}
          onChange={(e) => setFilterSector(e.target.value)}
          className={styles.sectorSelect}
        >
          <option value="">全セクター</option>
          <option value="輸送用機器">輸送用機器</option>
          <option value="情報・通信業">情報・通信業</option>
          <option value="電気機器">電気機器</option>
          <option value="化学">化学</option>
          <option value="銀行業">銀行業</option>
        </select>
        <button className={styles.csvButton}>
          <Download size={18} />
          CSV
        </button>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead className={styles.tableHead}>
            <tr>
              <th className={styles.th}>⭐</th>
              <th className={`${styles.th} ${styles.sortable}`} onClick={() => handleSort('code')}>
                銘柄 {sortBy === 'code' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('price')}>
                現在値 {sortBy === 'price' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('change')}>
                変動率 {sortBy === 'change' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignCenter}`} onClick={() => handleSort('fundamental')}>
                ファンダ {sortBy === 'fundamental' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignCenter}`} onClick={() => handleSort('supply')}>
                需給 {sortBy === 'supply' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignCenter}`} onClick={() => handleSort('risk')}>
                リスク {sortBy === 'risk' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignCenter}`} onClick={() => handleSort('overall')}>
                総合 {sortBy === 'overall' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={styles.th}>セクター</th>
              <th className={`${styles.th} ${styles.alignCenter}`}>詳細</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map((stock) => (
              <tr key={stock.code} className={styles.tableRow}>
                <td className={styles.td}>
                  <button onClick={() => toggleFavorite(stock.code)} className={styles.favoriteBtn}>
                    <Star size={18} className={favorites.includes(stock.code) ? styles.favoriteActive : styles.favoriteInactive} />
                  </button>
                </td>
                <td className={styles.td}>
                  <div className={styles.stockCode}>{stock.code}</div>
                  <div className={styles.stockName}>{stock.name}</div>
                </td>
                <td className={`${styles.td} ${styles.alignRight} ${styles.price}`}>
                  ¥{stock.price.toLocaleString()}
                </td>
                <td className={`${styles.td} ${styles.alignRight} ${styles.change} ${stock.change > 0 ? styles.positive : styles.negative}`}>
                  {stock.change > 0 ? '+' : ''}{stock.change}%
                </td>
                <td className={`${styles.td} ${styles.alignCenter}`}>
                  <ScoreCircle score={stock.fundamental} size="sm" />
                </td>
                <td className={`${styles.td} ${styles.alignCenter}`}>
                  <ScoreCircle score={stock.supply} size="sm" />
                </td>
                <td className={`${styles.td} ${styles.alignCenter}`}>
                  <ScoreCircle score={stock.risk} size="sm" />
                </td>
                <td className={`${styles.td} ${styles.alignCenter}`}>
                  <ScoreCircle score={stock.overall} />
                </td>
                <td className={`${styles.td} ${styles.sector}`}>{stock.sector}</td>
                <td className={`${styles.td} ${styles.alignCenter}`}>
                  <button
                    onClick={() => { setSelectedStock(stock); setCurrentScreen('detail'); }}
                    className={styles.detailButton}
                  >
                    <ChevronRight size={20} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className={styles.footer}>
        <div className={styles.footerText}>
          全{filteredStocks.length}件を表示
        </div>
        <div className={styles.footerText}>
          ソート: {getSortLabel()} ({sortDir === 'asc' ? '昇順' : '降順'})
        </div>
      </div>
    </div>
  );
}