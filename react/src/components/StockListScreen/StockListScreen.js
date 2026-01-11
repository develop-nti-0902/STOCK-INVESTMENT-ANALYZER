import React, { useState } from 'react';
import { Star, Download, ChevronRight, Plus, X } from 'lucide-react';
import ScoreCircle from '../common/ScoreCircle';
import styles from './StockListScreen.module.css';

// 投資スタイル別の損切・利確計算式
const INVESTMENT_STYLES = {
  aggressive: {
    label: '攻め (ハイリスク・ハイリターン)',
    stopLossPercent: -8,    // 損切: -8%
    takeProfitPercent: 25,  // 利確: +25%
    description: '短期的な大きな利益を狙う。変動リスクが高い。'
  },
  balanced: {
    label: 'バランス (中リスク・中リターン)',
    stopLossPercent: -5,    // 損切: -5%
    takeProfitPercent: 15,  // 利確: +15%
    description: 'リスクとリターンのバランスを重視。'
  },
  conservative: {
    label: '守り (低リスク・低リターン)',
    stopLossPercent: -3,    // 損切: -3%
    takeProfitPercent: 10,  // 利確: +10%
    description: '損失を最小限に抑え、着実な利益を目指す。'
  }
};

export default function StockListScreen({ stockList, favorites, toggleFavorite, setSelectedStock, setCurrentScreen, onRegisterStocks }) {
  // 検索・フィルター State
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSector, setFilterSector] = useState('');
  const [filterMarket, setFilterMarket] = useState('');
  const [filterValuation, setFilterValuation] = useState('');
  const [priceMin, setPriceMin] = useState('');
  const [priceMax, setPriceMax] = useState('');
  const [sortBy, setSortBy] = useState('overall');
  const [sortDir, setSortDir] = useState('desc');
  
  // 選択・登録 State
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [registrationData, setRegistrationData] = useState({});
  const [investmentStyle, setInvestmentStyle] = useState('balanced');

  // フィルタリング処理
  const filteredStocks = stockList
    .filter(s => {
      // 検索ワード
      if (searchTerm && !s.name.includes(searchTerm) && !s.code.includes(searchTerm)) {
        return false;
      }
      // セクター
      if (filterSector && s.sector !== filterSector) {
        return false;
      }
      // 市場区分
      if (filterMarket && s.market !== filterMarket) {
        return false;
      }
      // 割安度
      if (filterValuation && s.valuation.level !== filterValuation) {
        return false;
      }
      // 株価範囲
      if (priceMin && s.price < Number(priceMin)) {
        return false;
      }
      if (priceMax && s.price > Number(priceMax)) {
        return false;
      }
      return true;
    })
    .sort((a, b) => {
      const mult = sortDir === 'asc' ? 1 : -1;
      if (sortBy === 'valuation') {
        return (a.valuation.score - b.valuation.score) * mult;
      }
      if (sortBy === 'code') {
        return a.code.localeCompare(b.code) * mult;
      }
      return (a[sortBy] - b[sortBy]) * mult;
    });

  // ソート処理
  const handleSort = (key) => {
    if (sortBy === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortDir('desc');
    }
  };

  // ラベル取得
  const getSortLabel = () => {
    const labels = {
      code: '銘柄コード',
      price: '現在値',
      change: '変動率',
      valuation: '割安度',
      fundamental: 'ファンダ',
      supply: '需給',
      risk: 'リスク',
      overall: '総合スコア'
    };
    return labels[sortBy];
  };

  // チェックボックス処理
  const handleSelectStock = (stockCode) => {
    setSelectedStocks(prev => {
      if (prev.includes(stockCode)) {
        return prev.filter(code => code !== stockCode);
      } else {
        return [...prev, stockCode];
      }
    });
  };

  const handleSelectAll = () => {
    if (selectedStocks.length === filteredStocks.length) {
      setSelectedStocks([]);
    } else {
      setSelectedStocks(filteredStocks.map(s => s.code));
    }
  };

  // 損切・利確ラインの計算
  const calculateTradingLines = (price, style) => {
    const config = INVESTMENT_STYLES[style];
    return {
      stopLoss: Math.round(price * (1 + config.stopLossPercent / 100)),
      takeProfit: Math.round(price * (1 + config.takeProfitPercent / 100))
    };
  };

  // 登録モーダル表示
  const handleOpenRegisterModal = () => {
    const initialData = {};
    selectedStocks.forEach(code => {
      const stock = stockList.find(s => s.code === code);
      const lines = calculateTradingLines(stock.price, investmentStyle);
      initialData[code] = {
        code: code,
        name: stock.name,
        currentPrice: stock.price,
        shares: 100,
        stopLoss: lines.stopLoss,
        takeProfit: lines.takeProfit
      };
    });
    setRegistrationData(initialData);
    setShowRegisterModal(true);
  };

  // 投資スタイル変更時に全銘柄の損切・利確を再計算
  const handleStyleChange = (newStyle) => {
    setInvestmentStyle(newStyle);
    const updatedData = {};
    Object.keys(registrationData).forEach(code => {
      const data = registrationData[code];
      const lines = calculateTradingLines(data.currentPrice, newStyle);
      updatedData[code] = {
        ...data,
        stopLoss: lines.stopLoss,
        takeProfit: lines.takeProfit
      };
    });
    setRegistrationData(updatedData);
  };

  // 登録データ更新
  const updateRegistrationData = (code, field, value) => {
    setRegistrationData(prev => ({
      ...prev,
      [code]: {
        ...prev[code],
        [field]: value
      }
    }));
  };

  // 登録実行
  const handleRegister = () => {
    const stocksToRegister = Object.values(registrationData);
    onRegisterStocks(stocksToRegister);
    setShowRegisterModal(false);
    setSelectedStocks([]);
    setRegistrationData({});
  };

  // ユニークなセクター・市場取得
  const uniqueSectors = [...new Set(stockList.map(s => s.sector))].sort();
  const uniqueMarkets = [...new Set(stockList.map(s => s.market))].sort();

  return (
    <div className={styles.container}>
      {/* 検索・フィルターバー */}
      <div className={styles.searchSection}>
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
            className={styles.select}
          >
            <option value="">全セクター</option>
            {uniqueSectors.map(sector => (
              <option key={sector} value={sector}>{sector}</option>
            ))}
          </select>

          <select
            value={filterMarket}
            onChange={(e) => setFilterMarket(e.target.value)}
            className={styles.select}
          >
            <option value="">全市場</option>
            {uniqueMarkets.map(market => (
              <option key={market} value={market}>{market}</option>
            ))}
          </select>

          <select
            value={filterValuation}
            onChange={(e) => setFilterValuation(e.target.value)}
            className={styles.select}
          >
            <option value="">全割安度</option>
            <option value="bargain">割安のみ</option>
            <option value="fair">やや割安のみ</option>
            <option value="neutral">適正のみ</option>
            <option value="expensive">やや割高のみ</option>
            <option value="overvalued">割高のみ</option>
          </select>
        </div>

        <div className={styles.priceFilter}>
          <label className={styles.priceLabel}>株価範囲:</label>
          <input
            type="number"
            placeholder="最小"
            value={priceMin}
            onChange={(e) => setPriceMin(e.target.value)}
            className={styles.priceInput}
          />
          <span className={styles.priceSeparator}>〜</span>
          <input
            type="number"
            placeholder="最大"
            value={priceMax}
            onChange={(e) => setPriceMax(e.target.value)}
            className={styles.priceInput}
          />
          <button onClick={handleOpenRegisterModal} className={styles.registerButton} disabled={selectedStocks.length === 0}>
            <Plus size={18} />
            選択した銘柄を登録 ({selectedStocks.length})
          </button>
          <button className={styles.csvButton}>
            <Download size={18} />
            CSV
          </button>
        </div>
      </div>

      {/* テーブル */}
      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead className={styles.tableHead}>
            <tr>
              <th className={styles.th}>
                <input
                  type="checkbox"
                  checked={selectedStocks.length === filteredStocks.length && filteredStocks.length > 0}
                  onChange={handleSelectAll}
                  className={styles.checkbox}
                />
              </th>
              <th className={styles.th}>⭐</th>
              <th className={`${styles.th} ${styles.sortable}`} onClick={() => handleSort('code')}>
                銘柄 {sortBy === 'code' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={styles.th}>市場</th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('price')}>
                現在値 {sortBy === 'price' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('change')}>
                変動率 {sortBy === 'change' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignCenter}`} onClick={() => handleSort('valuation')}>
                割安度 {sortBy === 'valuation' && (sortDir === 'asc' ? '↑' : '↓')}
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
                  <input
                    type="checkbox"
                    checked={selectedStocks.includes(stock.code)}
                    onChange={() => handleSelectStock(stock.code)}
                    className={styles.checkbox}
                  />
                </td>
                <td className={styles.td}>
                  <button onClick={() => toggleFavorite(stock.code)} className={styles.favoriteBtn}>
                    <Star size={18} className={favorites.includes(stock.code) ? styles.favoriteActive : styles.favoriteInactive} />
                  </button>
                </td>
                <td className={styles.td}>
                  <div className={styles.stockCode}>{stock.code}</div>
                  <div className={styles.stockName}>{stock.name}</div>
                </td>
                <td className={styles.td}>
                  <span className={styles.marketBadge}>{stock.market}</span>
                </td>
                <td className={`${styles.td} ${styles.alignRight} ${styles.price}`}>
                  ¥{stock.price.toLocaleString()}
                </td>
                <td className={`${styles.td} ${styles.alignRight} ${styles.change} ${stock.change > 0 ? styles.positive : styles.negative}`}>
                  {stock.change > 0 ? '+' : ''}{stock.change}%
                </td>
                <td className={`${styles.td} ${styles.alignCenter}`}>
                  <div 
                    className={styles.valuationBadge}
                    style={{ 
                      backgroundColor: `${stock.valuation.color}20`,
                      color: stock.valuation.color,
                      border: `1px solid ${stock.valuation.color}40`
                    }}
                    title={stock.valuation.reasons.join('\n')}
                  >
                    {stock.valuation.label}
                  </div>
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

      {/* フッター */}
      <div className={styles.footer}>
        <div className={styles.footerText}>
          全{filteredStocks.length}件を表示 ({selectedStocks.length}件選択中)
        </div>
        <div className={styles.footerText}>
          ソート: {getSortLabel()} ({sortDir === 'asc' ? '昇順' : '降順'})
        </div>
      </div>

      {/* 登録モーダル */}
      {showRegisterModal && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>持ち株登録</h3>
              <button onClick={() => setShowRegisterModal(false)} className={styles.modalCloseButton}>
                <X size={24} />
              </button>
            </div>
            
            {/* 投資スタイル選択 */}
            <div className={styles.styleSelector}>
              <div className={styles.styleSelectorLabel}>投資スタイル</div>
              <div className={styles.styleOptions}>
                {Object.entries(INVESTMENT_STYLES).map(([key, style]) => (
                  <button
                    key={key}
                    onClick={() => handleStyleChange(key)}
                    className={`${styles.styleOption} ${investmentStyle === key ? styles.styleOptionActive : ''}`}
                  >
                    <div className={styles.styleOptionLabel}>{style.label}</div>
                    <div className={styles.styleOptionDetails}>
                      損切: {style.stopLossPercent}% / 利確: +{style.takeProfitPercent}%
                    </div>
                  </button>
                ))}
              </div>
              <div className={styles.styleDescription}>
                {INVESTMENT_STYLES[investmentStyle].description}
              </div>
            </div>

            <div className={styles.modalContent}>
              {Object.values(registrationData).map((data) => {
                const stopLossPercent = ((data.stopLoss - data.currentPrice) / data.currentPrice * 100).toFixed(1);
                const takeProfitPercent = ((data.takeProfit - data.currentPrice) / data.currentPrice * 100).toFixed(1);
                
                return (
                  <div key={data.code} className={styles.registrationItem}>
                    <div className={styles.registrationHeader}>
                      <strong>{data.code} {data.name}</strong>
                      <span className={styles.currentPriceLabel}>現在値: ¥{data.currentPrice.toLocaleString()}</span>
                    </div>
                    <div className={styles.registrationFields}>
                      <div className={styles.field}>
                        <label>株数</label>
                        <input
                          type="number"
                          value={data.shares}
                          onChange={(e) => updateRegistrationData(data.code, 'shares', Number(e.target.value))}
                          className={styles.fieldInput}
                        />
                        <span className={styles.fieldUnit}>株</span>
                      </div>
                      <div className={styles.field}>
                        <label>損切ライン</label>
                        <input
                          type="number"
                          value={data.stopLoss}
                          onChange={(e) => updateRegistrationData(data.code, 'stopLoss', Number(e.target.value))}
                          className={styles.fieldInput}
                        />
                        <span className={styles.fieldUnit}>円</span>
                        <span className={styles.percentageIndicator} style={{ color: '#ef4444' }}>
                          {stopLossPercent}%
                        </span>
                      </div>
                      <div className={styles.field}>
                        <label>利確ライン</label>
                        <input
                          type="number"
                          value={data.takeProfit}
                          onChange={(e) => updateRegistrationData(data.code, 'takeProfit', Number(e.target.value))}
                          className={styles.fieldInput}
                        />
                        <span className={styles.fieldUnit}>円</span>
                        <span className={styles.percentageIndicator} style={{ color: '#10b981' }}>
                          +{takeProfitPercent}%
                        </span>
                      </div>
                    </div>
                    {/* 視覚的なゲージ */}
                    <div className={styles.priceGauge}>
                      <div className={styles.gaugeBar}>
                        <div className={styles.gaugeStopLoss} style={{ width: '30%' }}>
                          <span>損切</span>
                        </div>
                        <div className={styles.gaugeCurrent} style={{ width: '40%' }}>
                          <span>現在値</span>
                        </div>
                        <div className={styles.gaugeTakeProfit} style={{ width: '30%' }}>
                          <span>利確</span>
                        </div>
                      </div>
                      <div className={styles.gaugeValues}>
                        <span className={styles.gaugeValueStopLoss}>¥{data.stopLoss.toLocaleString()}</span>
                        <span className={styles.gaugeValueCurrent}>¥{data.currentPrice.toLocaleString()}</span>
                        <span className={styles.gaugeValueTakeProfit}>¥{data.takeProfit.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className={styles.modalFooter}>
              <button onClick={() => setShowRegisterModal(false)} className={styles.cancelButton}>
                キャンセル
              </button>
              <button onClick={handleRegister} className={styles.confirmButton}>
                登録する
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}