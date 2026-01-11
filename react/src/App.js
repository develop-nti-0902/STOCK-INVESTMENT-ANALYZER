import React, { useState } from 'react'
import Header from './components/Header/Header'
import DashboardScreen from './components/DashboardScreen/DashboardScreen'
import StockListScreen from './components/StockListScreen/StockListScreen'
import TradeHistoryScreen from './components/TradeHistoryScreen/TradeHistoryScreen'
import ScoreSettingsScreen from './components/ScoreSettingsScreen/ScoreSettingsScreen'
import DataConnectionScreen from './components/DataConnectionScreen/DataConnectionScreen'
import AlertSettingsScreen from './components/AlertSettingsScreen/AlertSettingsScreen'
import StockDetailScreen from './components/StockDetailScreen/StockDetailScreen'
import styles from './App.module.css'

export default function App() {
	const [currentScreen, setCurrentScreen] = useState('dashboard')

	const [favorites, setFavorites] = useState([])
	const [selectedStock, setSelectedStock] = useState(null)

	const [scoreWeights, setScoreWeights] = useState({ fundamental: 40, supply: 40, risk: 20 })

	const toggleFavorite = (code) => {
		setFavorites((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]))
	}

	const portfolioData = {
		totalValue: 1_234_5670,
		unrealizedPL: 123450,
		unrealizedPLPercent: 5.2,
		realizedPLYear: 98765,
		overallScore: '◎',
		holdings: [
			{ code: '7203', name: 'トヨタ自動車', sector: '輸送用機器', currentPrice: 2650, plPercent: 3.2, fundamental: 85, supply: 70, risk: 40, overall: 80 },
			{ code: '6758', name: 'ソニーG', sector: '電気機器', currentPrice: 13000, plPercent: -1.5, fundamental: 78, supply: 65, risk: 50, overall: 75 },
			{ code: '6861', name: 'キーエンス', sector: '電気機器', currentPrice: 65000, plPercent: 2.1, fundamental: 90, supply: 60, risk: 30, overall: 88 },
			{ code: '9984', name: 'ソフトバンクG', sector: '情報・通信業', currentPrice: 8100, plPercent: -0.8, fundamental: 70, supply: 80, risk: 60, overall: 72 },
			{ code: '4063', name: '信越化学', sector: '化学', currentPrice: 4350, plPercent: 4.0, fundamental: 82, supply: 68, risk: 45, overall: 79 },
		],
	}

	const stockList = portfolioData.holdings.map(h => ({
		code: h.code,
		name: h.name,
		sector: h.sector,
		price: h.currentPrice,
		change: h.plPercent,
		fundamental: h.fundamental,
		supply: h.supply,
		risk: h.risk,
		overall: h.overall,
	}))

	return (
		<div className={styles.app}>
			<Header currentScreen={currentScreen} setCurrentScreen={setCurrentScreen} />
			{currentScreen === 'dashboard' && (
				<DashboardScreen portfolioData={portfolioData} favorites={favorites} toggleFavorite={toggleFavorite} />
			)}
			{currentScreen === 'list' && (
				<StockListScreen
					stockList={stockList}
					favorites={favorites}
					toggleFavorite={toggleFavorite}
					setSelectedStock={setSelectedStock}
					setCurrentScreen={setCurrentScreen}
				/>
			)}
			{currentScreen === 'detail' && (
				<StockDetailScreen stock={selectedStock} setCurrentScreen={setCurrentScreen} />
			)}
			{currentScreen === 'history' && (
				<TradeHistoryScreen />
			)}
			{currentScreen === 'settings' && (
				<ScoreSettingsScreen scoreWeights={scoreWeights} setScoreWeights={setScoreWeights} />
			)}
			{currentScreen === 'data' && (
				<DataConnectionScreen />
			)}
			{currentScreen === 'alerts' && (
				<AlertSettingsScreen />
			)}
		</div>
	)
}
