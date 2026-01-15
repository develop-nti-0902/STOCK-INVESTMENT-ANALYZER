import React, { useState } from 'react';
import { Star, Download, ChevronRight, Plus, X } from 'lucide-react';
import ScoreCircle from '../common/ScoreCircle';
import styles from './StockListScreen.module.css';

// 投資スタイル別の損切・利確計算式
const INVESTMENT_STYLES = {
  aggressive: {
    label: '攻め (ハイリスク・ハイリターン)',
    stopLossPercent: -8,
    takeProfitPercent: 25,
    description: '短期的な大きな利益を狙う。変動リスクが高い。'
  },
  balanced: {
    label: 'バランス (中リスク・中リターン)',
    stopLossPercent: -5,
    takeProfitPercent: 15,
    description: 'リスクとリターンのバランスを重視。'
  },
  conservative: {
    label: '守り (低リスク・低リターン)',
    stopLossPercent: -3,
    takeProfitPercent: 10,
    description: '損失を最小限に抑え、着実な利益を目指す。'
  }
};

// プリセット検索条件
const PRESET_FILTERS = {
  bargainDividend: {
    name: '割安高配当株',
    description: '割安で配当利回りが高く、財務健全な銘柄',
    filters: {
      pbrMax: 1.0,
      perMax: 15,
      dividendYieldMin: 3.0,
      equityRatioMin: 40,
      roeMin: 8
    }
  },
  growth: {
    name: '成長株',
    description: '高いEPS成長率と収益性を持つ銘柄',
    filters: {
      epsGrowthMin: 15,
      roeMin: 15,
      operatingMarginMin: 10,
      equityRatioMin: 30
    }
  },
  stableDividend: {
    name: '安定配当株',
    description: '高配当で財務が安定している銘柄',
    filters: {
      dividendYieldMin: 3.5,
      equityRatioMin: 50,
      debtRatioMax: 1.0,
      operatingMarginMin: 8
    }
  },
  value: {
    name: '割安株（バリュー）',
    description: 'PBR・PERが低く、割安な銘柄',
    filters: {
      pbrMax: 0.8,
      perMax: 12,
      equityRatioMin: 35
    }
  },
  qualityGrowth: {
    name: '優良成長株',
    description: '高ROE・高成長率で財務健全な銘柄',
    filters: {
      roeMin: 20,
      epsGrowthMin: 10,
      equityRatioMin: 40,
      operatingMarginMin: 15
    }
  },
  cashRich: {
    name: 'キャッシュリッチ',
    description: 'フリーキャッシュフロー利回りが高い銘柄',
    filters: {
      fcfYieldMin: 5,
      operatingCashFlowMin: 1000,
      debtRatioMax: 1.5
    }
  },
  smallValue: {
    name: '小型割安株',
    description: '時価総額が小さく割安な銘柄',
    filters: {
      marketCapMax: 50000,
      pbrMax: 1.0,
      perMax: 15,
      equityRatioMin: 30
    }
  },
  defensive: {
    name: 'ディフェンシブ株',
    description: '財務超安定で配当もある守りの銘柄',
    filters: {
      equityRatioMin: 60,
      currentRatioMin: 150,
      debtRatioMax: 0.5,
      dividendYieldMin: 2.5,
      operatingMarginMin: 8
    }
  }
};

export default function StockListScreen({ stockList, setSelectedStock, setCurrentScreen, onRegisterStocks }) {
  // 検索・フィルター State
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSector, setFilterSector] = useState('');
  const [filterMarket, setFilterMarket] = useState('');
  const [filterValuation, setFilterValuation] = useState('');
  const [priceMin, setPriceMin] = useState('');
  const [priceMax, setPriceMax] = useState('');
  const [pbrMin, setPbrMin] = useState('');
  const [pbrMax, setPbrMax] = useState('');
  const [perMin, setPerMin] = useState('');
  const [perMax, setPerMax] = useState('');
  const [dividendYieldMin, setDividendYieldMin] = useState('');
  const [roeMin, setRoeMin] = useState('');
  const [equityRatioMin, setEquityRatioMin] = useState('');
  const [sortBy, setSortBy] = useState('overall');
  const [sortDir, setSortDir] = useState('desc');
  
  // 追加フィルター State
  const [marketCapMin, setMarketCapMin] = useState('');
  const [marketCapMax, setMarketCapMax] = useState('');
  const [volumeMin, setVolumeMin] = useState('');
  const [operatingMarginMin, setOperatingMarginMin] = useState('');
  const [debtRatioMax, setDebtRatioMax] = useState('');
  const [currentRatioMin, setCurrentRatioMin] = useState('');
  const [fcfYieldMin, setFcfYieldMin] = useState('');
  const [epsGrowthMin, setEpsGrowthMin] = useState('');
  const [operatingCashFlowMin, setOperatingCashFlowMin] = useState('');
  
  // UI State
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [activePreset, setActivePreset] = useState(null);

  // 選択・登録 State
  const [selectedStocks, setSelectedStocks] = useState([]);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [registrationData, setRegistrationData] = useState({});
  const [investmentStyle, setInvestmentStyle] = useState('balanced');

  // フィルタリング処理
  const filteredStocks = stockList
    .filter(s => {
      if (searchTerm && !s.name.includes(searchTerm) && !s.code.includes(searchTerm)) {
        return false;
      }
      if (filterSector && s.sector !== filterSector) {
        return false;
      }
      if (filterMarket && s.market !== filterMarket) {
        return false;
      }
      if (filterValuation && s.valuation.level !== filterValuation) {
        return false;
      }
      if (priceMin && s.price < Number(priceMin)) {
        return false;
      }
      if (priceMax && s.price > Number(priceMax)) {
        return false;
      }
      if (pbrMin && s.pbr < Number(pbrMin)) {
        return false;
      }
      if (pbrMax && s.pbr > Number(pbrMax)) {
        return false;
      }
      if (perMin && s.per < Number(perMin)) {
        return false;
      }
      if (perMax && s.per > Number(perMax)) {
        return false;
      }
      if (dividendYieldMin && s.dividendYield < Number(dividendYieldMin)) {
        return false;
      }
      if (roeMin && s.roe < Number(roeMin)) {
        return false;
      }
      if (equityRatioMin && s.equityRatio < Number(equityRatioMin)) {
        return false;
      }
      if (marketCapMin && s.marketCap < Number(marketCapMin)) {
        return false;
      }
      if (marketCapMax && s.marketCap > Number(marketCapMax)) {
        return false;
      }
      if (volumeMin && s.volume < Number(volumeMin)) {
        return false;
      }
      if (operatingMarginMin && s.operatingMargin < Number(operatingMarginMin)) {
        return false;
      }
      if (debtRatioMax && s.debtRatio > Number(debtRatioMax)) {
        return false;
      }
      if (currentRatioMin && s.currentRatio < Number(currentRatioMin)) {
        return false;
      }
      if (fcfYieldMin && s.fcfYield < Number(fcfYieldMin)) {
        return false;
      }
      if (epsGrowthMin && s.epsGrowth < Number(epsGrowthMin)) {
        return false;
      }
      if (operatingCashFlowMin && s.operatingCashFlow < Number(operatingCashFlowMin) * 1000000) {
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
      valuation: '割安度',
      pbr: 'PBR',
      per: 'PER',
      evEbitda: 'EV/EBITDA',
      dividendYield: '配当利回り',
      fcfYield: 'FCF利回り',
      roe: 'ROE',
      roa: 'ROA',
      operatingMargin: '営業利益率',
      epsGrowth: 'EPS成長率',
      equityRatio: '自己資本比率',
      debtRatio: '有利子負債倍率',
      currentRatio: '流動比率',
      operatingCashFlow: '営業CF',
      investingCashFlow: '投資CF',
      freeCashFlow: 'フリーCF'
    };
    return labels[sortBy] || sortBy;
  };

  // すべてのフィルターをクリア
  const clearAllFilters = () => {
    setSearchTerm('');
    setFilterSector('');
    setFilterMarket('');
    setFilterValuation('');
    setPriceMin('');
    setPriceMax('');
    setPbrMin('');
    setPbrMax('');
    setPerMin('');
    setPerMax('');
    setDividendYieldMin('');
    setRoeMin('');
    setEquityRatioMin('');
    setMarketCapMin('');
    setMarketCapMax('');
    setVolumeMin('');
    setOperatingMarginMin('');
    setDebtRatioMax('');
    setCurrentRatioMin('');
    setFcfYieldMin('');
    setEpsGrowthMin('');
    setOperatingCashFlowMin('');
    setActivePreset(null);
  };

  // プリセット適用
  const applyPreset = (presetKey) => {
    const preset = PRESET_FILTERS[presetKey];
    if (!preset) return;

    clearAllFilters();

    const filters = preset.filters;
    if (filters.pbrMax !== undefined) setPbrMax(filters.pbrMax.toString());
    if (filters.pbrMin !== undefined) setPbrMin(filters.pbrMin.toString());
    if (filters.perMax !== undefined) setPerMax(filters.perMax.toString());
    if (filters.perMin !== undefined) setPerMin(filters.perMin.toString());
    if (filters.dividendYieldMin !== undefined) setDividendYieldMin(filters.dividendYieldMin.toString());
    if (filters.equityRatioMin !== undefined) setEquityRatioMin(filters.equityRatioMin.toString());
    if (filters.roeMin !== undefined) setRoeMin(filters.roeMin.toString());
    if (filters.epsGrowthMin !== undefined) setEpsGrowthMin(filters.epsGrowthMin.toString());
    if (filters.operatingMarginMin !== undefined) setOperatingMarginMin(filters.operatingMarginMin.toString());
    if (filters.debtRatioMax !== undefined) setDebtRatioMax(filters.debtRatioMax.toString());
    if (filters.fcfYieldMin !== undefined) setFcfYieldMin(filters.fcfYieldMin.toString());
    if (filters.marketCapMax !== undefined) setMarketCapMax(filters.marketCapMax.toString());
    if (filters.marketCapMin !== undefined) setMarketCapMin(filters.marketCapMin.toString());
    if (filters.currentRatioMin !== undefined) setCurrentRatioMin(filters.currentRatioMin.toString());
    if (filters.operatingCashFlowMin !== undefined) setOperatingCashFlowMin(filters.operatingCashFlowMin.toString());

    setActivePreset(presetKey);
  };

  // アクティブなフィルター数をカウント
  const getActiveFilterCount = () => {
    let count = 0;
    if (searchTerm) count++;
    if (filterSector) count++;
    if (filterMarket) count++;
    if (filterValuation) count++;
    if (priceMin) count++;
    if (priceMax) count++;
    if (pbrMin) count++;
    if (pbrMax) count++;
    if (perMin) count++;
    if (perMax) count++;
    if (dividendYieldMin) count++;
    if (roeMin) count++;
    if (equityRatioMin) count++;
    if (marketCapMin) count++;
    if (marketCapMax) count++;
    if (volumeMin) count++;
    if (operatingMarginMin) count++;
    if (debtRatioMax) count++;
    if (currentRatioMin) count++;
    if (fcfYieldMin) count++;
    if (epsGrowthMin) count++;
    if (operatingCashFlowMin) count++;
    return count;
  };

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

  const calculateTradingLines = (price, style) => {
    const config = INVESTMENT_STYLES[style];
    return {
      stopLoss: Math.round(price * (1 + config.stopLossPercent / 100)),
      takeProfit: Math.round(price * (1 + config.takeProfitPercent / 100))
    };
  };

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

  const updateRegistrationData = (code, field, value) => {
    setRegistrationData(prev => ({
      ...prev,
      [code]: {
        ...prev[code],
        [field]: value
      }
    }));
  };

  const handleRegister = () => {
    const stocksToRegister = Object.values(registrationData);
    onRegisterStocks(stocksToRegister);
    setShowRegisterModal(false);
    setSelectedStocks([]);
    setRegistrationData({});
  };

  const uniqueSectors = [...new Set(stockList.map(s => s.sector))].sort();
  const uniqueMarkets = [...new Set(stockList.map(s => s.market))].sort();

  return (
    <div className={styles.container}>
      {/* プリセット検索セクション */}
      <div className={styles.presetSection}>
        <div className={styles.presetHeader}>
          <h3 className={styles.presetTitle}>クイック検索</h3>
          {activePreset && (
            <div className={styles.activePresetBadge}>
              適用中: {PRESET_FILTERS[activePreset].name}
            </div>
          )}
        </div>
        <div className={styles.presetGrid}>
          {Object.entries(PRESET_FILTERS).map(([key, preset]) => (
            <button
              key={key}
              onClick={() => applyPreset(key)}
              className={`${styles.presetCard} ${activePreset === key ? styles.presetCardActive : ''}`}
            >
              <div className={styles.presetCardTitle}>{preset.name}</div>
              <div className={styles.presetCardDescription}>{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

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

        <div className={styles.filterRow}>
          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>株価:</label>
            <input
              type="number"
              placeholder="最小"
              value={priceMin}
              onChange={(e) => setPriceMin(e.target.value)}
              className={styles.filterInput}
            />
            <span className={styles.filterSeparator}>〜</span>
            <input
              type="number"
              placeholder="最大"
              value={priceMax}
              onChange={(e) => setPriceMax(e.target.value)}
              className={styles.filterInput}
            />
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>PBR:</label>
            <input
              type="number"
              step="0.1"
              placeholder="最小"
              value={pbrMin}
              onChange={(e) => setPbrMin(e.target.value)}
              className={styles.filterInput}
            />
            <span className={styles.filterSeparator}>〜</span>
            <input
              type="number"
              step="0.1"
              placeholder="最大"
              value={pbrMax}
              onChange={(e) => setPbrMax(e.target.value)}
              className={styles.filterInput}
            />
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>PER:</label>
            <input
              type="number"
              step="0.1"
              placeholder="最小"
              value={perMin}
              onChange={(e) => setPerMin(e.target.value)}
              className={styles.filterInput}
            />
            <span className={styles.filterSeparator}>〜</span>
            <input
              type="number"
              step="0.1"
              placeholder="最大"
              value={perMax}
              onChange={(e) => setPerMax(e.target.value)}
              className={styles.filterInput}
            />
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>配当利回り:</label>
            <input
              type="number"
              step="0.1"
              placeholder="最小%"
              value={dividendYieldMin}
              onChange={(e) => setDividendYieldMin(e.target.value)}
              className={styles.filterInput}
            />
            <span className={styles.filterUnit}>%以上</span>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>ROE:</label>
            <input
              type="number"
              step="0.1"
              placeholder="最小%"
              value={roeMin}
              onChange={(e) => setRoeMin(e.target.value)}
              className={styles.filterInput}
            />
            <span className={styles.filterUnit}>%以上</span>
          </div>

          <div className={styles.filterGroup}>
            <label className={styles.filterLabel}>自己資本比率:</label>
            <input
              type="number"
              step="0.1"
              placeholder="最小%"
              value={equityRatioMin}
              onChange={(e) => setEquityRatioMin(e.target.value)}
              className={styles.filterInput}
            />
            <span className={styles.filterUnit}>%以上</span>
          </div>
        </div>

        <div className={styles.priceFilter}>
          <div className={styles.priceFilterLeft}>
            <button
              onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
              className={styles.advancedFilterToggle}
            >
              {showAdvancedFilters ? '詳細フィルターを隠す' : '詳細フィルターを表示'}
              {getActiveFilterCount() > 0 && (
                <span className={styles.filterCountBadge}>{getActiveFilterCount()}</span>
              )}
            </button>
            <button
              onClick={clearAllFilters}
              className={styles.clearButton}
            >
              すべてクリア
            </button>
          </div>
        </div>

        {showAdvancedFilters && (
          <div className={styles.advancedFilters}>
            <div className={styles.advancedFiltersTitle}>詳細フィルター</div>
            
            <div className={styles.filterRow}>
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>時価総額（億円）:</label>
                <input
                  type="number"
                  placeholder="最小"
                  value={marketCapMin}
                  onChange={(e) => setMarketCapMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterSeparator}>〜</span>
                <input
                  type="number"
                  placeholder="最大"
                  value={marketCapMax}
                  onChange={(e) => setMarketCapMax(e.target.value)}
                  className={styles.filterInput}
                />
              </div>

              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>出来高:</label>
                <input
                  type="number"
                  placeholder="最小"
                  value={volumeMin}
                  onChange={(e) => setVolumeMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>株以上</span>
              </div>

              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>営業利益率:</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="最小%"
                  value={operatingMarginMin}
                  onChange={(e) => setOperatingMarginMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>%以上</span>
              </div>

              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>有利子負債倍率:</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="最大"
                  value={debtRatioMax}
                  onChange={(e) => setDebtRatioMax(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>倍以下</span>
              </div>
            </div>

            <div className={styles.filterRow}>
              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>流動比率:</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="最小%"
                  value={currentRatioMin}
                  onChange={(e) => setCurrentRatioMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>%以上</span>
              </div>

              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>FCF利回り:</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="最小%"
                  value={fcfYieldMin}
                  onChange={(e) => setFcfYieldMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>%以上</span>
              </div>

              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>EPS成長率:</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="最小%"
                  value={epsGrowthMin}
                  onChange={(e) => setEpsGrowthMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>%以上</span>
              </div>

              <div className={styles.filterGroup}>
                <label className={styles.filterLabel}>営業CF（百万円）:</label>
                <input
                  type="number"
                  placeholder="最小"
                  value={operatingCashFlowMin}
                  onChange={(e) => setOperatingCashFlowMin(e.target.value)}
                  className={styles.filterInput}
                />
                <span className={styles.filterUnit}>M以上</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 登録ボタン */}
      <div className={styles.actionBar}>
        <button onClick={handleOpenRegisterModal} className={styles.registerButton} disabled={selectedStocks.length === 0}>
          <Plus size={18} />
          選択した銘柄を登録 ({selectedStocks.length})
        </button>
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
              <th className={`${styles.th} ${styles.alignCenter}`}>詳細</th>
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
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('pbr')}>
                PBR {sortBy === 'pbr' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('per')}>
                PER {sortBy === 'per' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('evEbitda')}>
                EV/EBITDA {sortBy === 'evEbitda' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('dividendYield')}>
                配当利回り {sortBy === 'dividendYield' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('fcfYield')}>
                FCF利回り {sortBy === 'fcfYield' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('roe')}>
                ROE {sortBy === 'roe' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('roa')}>
                ROA {sortBy === 'roa' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('operatingMargin')}>
                営業利益率 {sortBy === 'operatingMargin' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('epsGrowth')}>
                EPS成長率 {sortBy === 'epsGrowth' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('equityRatio')}>
                自己資本比率 {sortBy === 'equityRatio' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('debtRatio')}>
                有利子負債倍率 {sortBy === 'debtRatio' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('currentRatio')}>
                流動比率 {sortBy === 'currentRatio' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('operatingCashFlow')}>
                営業CF {sortBy === 'operatingCashFlow' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('investingCashFlow')}>
                投資CF {sortBy === 'investingCashFlow' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={`${styles.th} ${styles.sortable} ${styles.alignRight}`} onClick={() => handleSort('freeCashFlow')}>
                フリーCF {sortBy === 'freeCashFlow' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className={styles.th}>セクター</th>
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
                <td className={styles.alignCenter}>
                  <button
                    onClick={() => {
                      setSelectedStock(stock);
                      setCurrentScreen('detail', 'list');
                    }}
                    className={styles.detailButton}
                    aria-label="詳細を見る"
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <circle cx="4" cy="5" r="2" />
                      <rect x="8" y="4" width="12" height="2" rx="1" />
                      <circle cx="4" cy="12" r="2" />
                      <rect x="8" y="11" width="12" height="2" rx="1" />
                      <circle cx="4" cy="19" r="2" />
                      <rect x="8" y="18" width="12" height="2" rx="1" />
                    </svg>
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
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.pbr?.toFixed(2) || '-'}</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.per?.toFixed(2) || '-'}</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.evEbitda?.toFixed(2) || '-'}</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.dividendYield?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.fcfYield?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.roe?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.roa?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.operatingMargin?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight} ${stock.epsGrowth > 0 ? styles.positive : styles.negative}`}>
                  {stock.epsGrowth > 0 ? '+' : ''}{stock.epsGrowth?.toFixed(2)}%
                </td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.equityRatio?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.debtRatio?.toFixed(2)}</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{stock.currentRatio?.toFixed(2)}%</td>
                <td className={`${styles.td} ${styles.alignRight}`}>{(stock.operatingCashFlow / 1000000).toFixed(0)}M</td>
                <td className={`${styles.td} ${styles.alignRight} ${stock.investingCashFlow < 0 ? styles.negative : ''}`}>
                  {(stock.investingCashFlow / 1000000).toFixed(0)}M
                </td>
                <td className={`${styles.td} ${styles.alignRight} ${stock.freeCashFlow > 0 ? styles.positive : styles.negative}`}>
                  {(stock.freeCashFlow / 1000000).toFixed(0)}M
                </td>
                <td className={`${styles.td} ${styles.sector}`}>{stock.sector}</td>
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