import React, { useState } from 'react';
import Header from './Header';
import DashboardScreen from './DashboardScreen';
import StockListScreen from './StockListScreen';
import StockDetailScreen from './StockDetailScreen';
import TradeHistoryScreen from './TradeHistoryScreen';
import ScoreSettingsScreen from './ScoreSettingsScreen';
import DataConnectionScreen from './DataConnectionScreen';
import AlertSettingsScreen from './AlertSettingsScreen';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('dashboard');
  const [selectedStock, setSelectedStock] = useState(null);
  const [favorites, setFavorites] = useState(['7203', '9984']);
  const [scoreWeights, setScoreWeights] = useState({
    fundamental: 40,
    supply: 40,
    risk: 20
  });

  // 共通データ
  const portfolioData = {
    totalValue: 15420000,
    unrealizedPL: 1234500,
    unrealizedPLPercent: 8.7,
    realizedPLYear: 567890,
    overallScore: '◎',
    holdings: [
      { code: '7203', name: 'トヨタ自動車', shares: 500, avgPrice: 2650, currentPrice: 2845, value: 1422500, plPercent: 7.4, sector: '輸送用機器', fundamental: 85, supply: 72, risk: 68, overall: 75 },
      { code: '9984', name: 'ソフトバンクG', shares: 200, avgPrice: 7800, currentPrice: 8234, value: 1646800, plPercent: 5.6, sector: '情報・通信業', fundamental: 78, supply: 85, risk: 55, overall: 73 },
      { code: '6758', name: 'ソニーG', shares: 100, avgPrice: 13000, currentPrice: 13560, value: 1356000, plPercent: 4.3, sector: '電気機器', fundamental: 88, supply: 80, risk: 72, overall: 80 },
      { code: '6861', name: 'キーエンス', shares: 20, avgPrice: 65000, currentPrice: 68900, value: 1378000, plPercent: 6.0, sector: '電気機器', fundamental: 92, supply: 65, risk: 78, overall: 78 },
      { code: '4063', name: '信越化学', shares: 300, avgPrice: 4350, currentPrice: 4582, value: 1374600, plPercent: 5.3, sector: '化学', fundamental: 82, supply: 75, risk: 80, overall: 79 }
    ]
  };

  const stockList = [
    { code: '7203', name: 'トヨタ自動車', price: 2845, change: -1.21, fundamental: 85, supply: 72, risk: 68, overall: 75, sector: '輸送用機器', marketCap: 42500000, per: 8.5, pbr: 0.95, roe: 11.2 },
    { code: '9984', name: 'ソフトバンクG', price: 8234, change: 1.93, fundamental: 78, supply: 85, risk: 55, overall: 73, sector: '情報・通信業', marketCap: 12300000, per: 12.3, pbr: 1.15, roe: 9.4 },
    { code: '6758', name: 'ソニーG', price: 13560, change: 1.65, fundamental: 88, supply: 80, risk: 72, overall: 80, sector: '電気機器', marketCap: 16700000, per: 15.7, pbr: 1.82, roe: 11.6 },
    { code: '6861', name: 'キーエンス', price: 68900, change: -1.71, fundamental: 92, supply: 65, risk: 78, overall: 78, sector: '電気機器', marketCap: 16200000, per: 45.2, pbr: 8.35, roe: 18.5 },
    { code: '4063', name: '信越化学', price: 4582, change: 1.73, fundamental: 82, supply: 75, risk: 80, overall: 79, sector: '化学', marketCap: 1850000, per: 18.9, pbr: 1.52, roe: 8.1 },
    { code: '8306', name: '三菱UFJFG', price: 1456, change: -0.82, fundamental: 75, supply: 78, risk: 85, overall: 79, sector: '銀行業', marketCap: 18900000, per: 11.2, pbr: 0.78, roe: 7.0 }
  ];

  const toggleFavorite = (code) => {
    setFavorites(prev =>
      prev.includes(code) ? prev.filter(c => c !== code) : [...prev, code]
    );
  };

  const renderScreen = () => {
    switch (currentScreen) {
      case 'dashboard':
        return <DashboardScreen portfolioData={portfolioData} favorites={favorites} toggleFavorite={toggleFavorite} />;
      case 'list':
        return <StockListScreen stockList={stockList} favorites={favorites} toggleFavorite={toggleFavorite} setSelectedStock={setSelectedStock} setCurrentScreen={setCurrentScreen} />;
      case 'detail':
        return <StockDetailScreen selectedStock={selectedStock} setCurrentScreen={setCurrentScreen} />;
      case 'history':
        return <TradeHistoryScreen />;
      case 'settings':
        return <ScoreSettingsScreen scoreWeights={scoreWeights} setScoreWeights={setScoreWeights} />;
      case 'data':
        return <DataConnectionScreen />;
      case 'alerts':
        return <AlertSettingsScreen />;
      default:
        return <DashboardScreen portfolioData={portfolioData} favorites={favorites} toggleFavorite={toggleFavorite} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <Header currentScreen={currentScreen} setCurrentScreen={setCurrentScreen} />
      <div className="max-w-7xl mx-auto p-8">
        {renderScreen()}
      </div>
    </div>
  );
}
