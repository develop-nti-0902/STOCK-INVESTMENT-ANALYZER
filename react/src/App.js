import React, { useState, useMemo } from 'react'
import Header from './components/Header/Header'
import DashboardScreen from './components/DashboardScreen/DashboardScreen'
import StockListScreen from './components/StockListScreen/StockListScreen'
import TradeHistoryScreen from './components/TradeHistoryScreen/TradeHistoryScreen'
import ScoreSettingsScreen from './components/ScoreSettingsScreen/ScoreSettingsScreen'
import DataConnectionScreen from './components/DataConnectionScreen/DataConnectionScreen'
import AlertSettingsScreen from './components/AlertSettingsScreen/AlertSettingsScreen'
import StockDetailScreen from './components/StockDetailScreen/StockDetailScreen'
import styles from './App.module.css'

// =====================================
// スコア計算ユーティリティ関数
// =====================================

/**
 * ファンダメンタルスコアを計算
 * @param {Object} stockData - 銘柄データ
 * @returns {number} ファンダメンタルスコア (0-100)
 */
const calculateFundamentalScore = (stockData) => {
  // PER: 低いほど良い (15以下=100点、30以上=0点)
  const perScore = Math.max(0, Math.min(100, ((30 - stockData.per) / 15) * 100))
  
  // PBR: 低いほど良い (1以下=100点、3以上=0点)
  const pbrScore = Math.max(0, Math.min(100, ((3 - stockData.pbr) / 2) * 100))
  
  // ROE: 高いほど良い (15%以上=100点、5%以下=0点)
  const roeScore = Math.max(0, Math.min(100, ((stockData.roe - 5) / 10) * 100))
  
  // 配当利回り: 高いほど良い (4%以上=100点、1%以下=0点)
  const dividendScore = Math.max(0, Math.min(100, ((stockData.dividendYield - 1) / 3) * 100))
  
  return Math.round((perScore + pbrScore + roeScore + dividendScore) / 4)
}

/**
 * 需給スコアを計算
 * @param {Object} stockData - 銘柄データ
 * @returns {number} 需給スコア (0-100)
 */
const calculateSupplyScore = (stockData) => {
  // 出来高比率: 高いほど良い (150%以上=100点、50%以下=0点)
  const volumeScore = Math.max(0, Math.min(100, ((stockData.volumeRatio - 50) / 100) * 100))
  
  // 信用倍率: 低いほど良い (1倍以下=100点、5倍以上=0点)
  const marginScore = Math.max(0, Math.min(100, ((5 - stockData.marginRatio) / 4) * 100))
  
  // 外国人保有比率: 30%が理想 (30%=100点、0%or60%以上=0点)
  const foreignScore = Math.max(0, 100 - Math.abs(stockData.foreignOwnership - 30) * (100 / 30))
  
  return Math.round((volumeScore + marginScore + foreignScore) / 3)
}

/**
 * リスクスコアを計算
 * @param {Object} stockData - 銘柄データ
 * @returns {number} リスクスコア (0-100、高いほど低リスク)
 */
const calculateRiskScore = (stockData) => {
  // ボラティリティ: 低いほど良い (10%以下=100点、40%以上=0点)
  const volatilityScore = Math.max(0, Math.min(100, ((40 - stockData.volatility) / 30) * 100))
  
  // ベータ値: 1に近いほど良い (1=100点、0or2以上=0点)
  const betaScore = Math.max(0, 100 - Math.abs(stockData.beta - 1) * 100)
  
  return Math.round((volatilityScore + betaScore) / 2)
}

/**
 * 各銘柄のスコアを計算
 * @param {Object} stockData - 銘柄データ
 * @returns {Object} 計算されたスコア {fundamental, supply, risk}
 */
const calculateScores = (stockData) => {
  return {
    fundamental: calculateFundamentalScore(stockData),
    supply: calculateSupplyScore(stockData),
    risk: calculateRiskScore(stockData)
  }
}

/**
 * 総合スコアを計算
 * @param {number} fundamental - ファンダメンタルスコア
 * @param {number} supply - 需給スコア
 * @param {number} risk - リスクスコア
 * @param {Object} weights - 重み付け設定
 * @returns {number} 総合スコア (0-100)
 */
const calculateOverallScore = (fundamental, supply, risk, weights) => {
  return Math.round(
    (fundamental * weights.fundamental + 
     supply * weights.supply + 
     risk * weights.risk) / 100
  )
}

/**
 * 総合スコアを◎○△×の記号に変換
 * @param {number} score - 総合スコア (0-100)
 * @returns {string} スコア記号
 */
const getScoreSymbol = (score) => {
  if (score >= 80) return '◎'
  if (score >= 60) return '○'
  if (score >= 40) return '△'
  return '×'
}

/**
 * 割安度を判定
 * @param {Object} stockData - 銘柄データ
 * @returns {Object} 割安判定結果 {level, score, reasons}
 */
const calculateValuation = (stockData) => {
  let score = 0
  const reasons = []
  
  // PER判定 (業種平均を15と仮定)
  if (stockData.per < 10) {
    score += 30
    reasons.push(`PER ${stockData.per}倍は非常に低い`)
  } else if (stockData.per < 15) {
    score += 20
    reasons.push(`PER ${stockData.per}倍は平均以下`)
  } else if (stockData.per > 25) {
    score -= 10
    reasons.push(`PER ${stockData.per}倍は割高水準`)
  }
  
  // PBR判定
  if (stockData.pbr < 1.0) {
    score += 25
    reasons.push(`PBR ${stockData.pbr}倍で純資産割れ水準`)
  } else if (stockData.pbr < 1.5) {
    score += 15
    reasons.push(`PBR ${stockData.pbr}倍は低水準`)
  } else if (stockData.pbr > 3.0) {
    score -= 10
    reasons.push(`PBR ${stockData.pbr}倍は割高水準`)
  }
  
  // ROE判定 (高ROE + 低PBRは割安)
  if (stockData.roe > 15 && stockData.pbr < 2.0) {
    score += 20
    reasons.push(`高ROE(${stockData.roe}%)で低PBRは魅力的`)
  } else if (stockData.roe < 5) {
    score -= 10
    reasons.push(`ROE ${stockData.roe}%は低収益性`)
  }
  
  // 配当利回り判定
  if (stockData.dividendYield > 4.0) {
    score += 15
    reasons.push(`配当利回り${stockData.dividendYield}%は高水準`)
  } else if (stockData.dividendYield > 2.5) {
    score += 10
    reasons.push(`配当利回り${stockData.dividendYield}%は平均以上`)
  }
  
  // PER/PBR複合判定 (グレアム指数的な考え方)
  const grahamIndex = stockData.per * stockData.pbr
  if (grahamIndex < 15) {
    score += 15
    reasons.push('PER×PBRが15未満で割安')
  }
  
  // 総合判定
  let level, label, color
  if (score >= 60) {
    level = 'bargain'
    label = '割安'
    color = '#10b981' // green
  } else if (score >= 30) {
    level = 'fair'
    label = 'やや割安'
    color = '#3b82f6' // blue
  } else if (score >= 0) {
    level = 'neutral'
    label = '適正'
    color = '#6b7280' // gray
  } else if (score >= -20) {
    level = 'expensive'
    label = 'やや割高'
    color = '#f59e0b' // orange
  } else {
    level = 'overvalued'
    label = '割高'
    color = '#ef4444' // red
  }
  
  return {
    level,
    label,
    color,
    score: Math.max(0, Math.min(100, score + 50)), // 0-100に正規化
    reasons: reasons.slice(0, 3) // 主要な理由を3つまで
  }
}

// =====================================
// メインコンポーネント
// =====================================

export default function App() {
  // ----------------
  // State管理
  // ----------------
  const [currentScreen, setCurrentScreen] = useState('dashboard')
  const [favorites, setFavorites] = useState([])
  const [selectedStock, setSelectedStock] = useState(null)
  const [scoreWeights, setScoreWeights] = useState({
    fundamental: 40,
    supply: 40,
    risk: 20
  })

  // ----------------
  // イベントハンドラー
  // ----------------
  const toggleFavorite = (code) => {
    setFavorites((prev) => 
      prev.includes(code) 
        ? prev.filter((c) => c !== code) 
        : [...prev, code]
    )
  }

  // ----------------
  // データ定義
  // ----------------
  // 実際の運用では、APIやデータベースから取得
  const rawStockData = [
    {
      code: '7203',
      name: 'トヨタ自動車',
      sector: '輸送用機器',
      currentPrice: 2650,
      plPercent: 3.2,
      per: 10.5,
      pbr: 1.2,
      roe: 12.5,
      dividendYield: 3.2,
      volumeRatio: 120,
      marginRatio: 1.8,
      foreignOwnership: 35,
      volatility: 18,
      beta: 0.95
    },
    {
      code: '6758',
      name: 'ソニーG',
      sector: '電気機器',
      currentPrice: 13000,
      plPercent: -1.5,
      per: 18.2,
      pbr: 2.1,
      roe: 14.8,
      dividendYield: 0.8,
      volumeRatio: 95,
      marginRatio: 2.5,
      foreignOwnership: 55,
      volatility: 25,
      beta: 1.15
    },
    {
      code: '6861',
      name: 'キーエンス',
      sector: '電気機器',
      currentPrice: 65000,
      plPercent: 2.1,
      per: 45.0,
      pbr: 8.5,
      roe: 22.0,
      dividendYield: 0.5,
      volumeRatio: 80,
      marginRatio: 0.8,
      foreignOwnership: 25,
      volatility: 22,
      beta: 0.85
    },
    {
      code: '9984',
      name: 'ソフトバンクG',
      sector: '情報・通信業',
      currentPrice: 8100,
      plPercent: -0.8,
      per: 12.5,
      pbr: 1.5,
      roe: 8.5,
      dividendYield: 5.2,
      volumeRatio: 180,
      marginRatio: 3.2,
      foreignOwnership: 42,
      volatility: 35,
      beta: 1.35
    },
    {
      code: '4063',
      name: '信越化学',
      sector: '化学',
      currentPrice: 4350,
      plPercent: 4.0,
      per: 14.8,
      pbr: 1.8,
      roe: 15.2,
      dividendYield: 2.8,
      volumeRatio: 105,
      marginRatio: 1.2,
      foreignOwnership: 28,
      volatility: 20,
      beta: 1.05
    },
  ]

  // ----------------
  // スコア計算 (useMemoで最適化)
  // ----------------
  const portfolioData = useMemo(() => {
    const holdings = rawStockData.map(stock => {
      const scores = calculateScores(stock)
      const overall = calculateOverallScore(
        scores.fundamental, 
        scores.supply, 
        scores.risk, 
        scoreWeights
      )
      const valuation = calculateValuation(stock)
      
      return {
        ...stock,
        ...scores,
        overall,
        valuation
      }
    })

    // ポートフォリオ全体の総合スコアを計算
    const avgOverallScore = Math.round(
      holdings.reduce((sum, h) => sum + h.overall, 0) / holdings.length
    )

    return {
      totalValue: 1_234_5670,
      unrealizedPL: 123450,
      unrealizedPLPercent: 5.2,
      realizedPLYear: 98765,
      overallScore: getScoreSymbol(avgOverallScore),
      holdings
    }
  }, [scoreWeights]) // scoreWeightsが変更されたときのみ再計算

  // ----------------
  // 銘柄リスト用データ (リアルタイムで総合スコアを再計算)
  // ----------------
  const stockList = useMemo(() => {
    return portfolioData.holdings.map(h => ({
      code: h.code,
      name: h.name,
      sector: h.sector,
      price: h.currentPrice,
      change: h.plPercent,
      fundamental: h.fundamental,
      supply: h.supply,
      risk: h.risk,
      overall: h.overall,
      valuation: h.valuation,
      // 詳細表示用の追加データ
      per: h.per,
      pbr: h.pbr,
      roe: h.roe,
      dividendYield: h.dividendYield,
      volumeRatio: h.volumeRatio,
      marginRatio: h.marginRatio,
      foreignOwnership: h.foreignOwnership,
      volatility: h.volatility,
      beta: h.beta,
      marketCap: 10000000 // ダミー値
    }))
  }, [portfolioData.holdings])

  // ----------------
  // 画面レンダリング関数
  // ----------------
  const renderScreen = () => {
    switch (currentScreen) {
      case 'dashboard':
        return (
          <DashboardScreen
            portfolioData={portfolioData}
            favorites={favorites}
            toggleFavorite={toggleFavorite}
          />
        )
      
      case 'list':
        return (
          <StockListScreen
            stockList={stockList}
            favorites={favorites}
            toggleFavorite={toggleFavorite}
            setSelectedStock={setSelectedStock}
            setCurrentScreen={setCurrentScreen}
          />
        )
      
      case 'detail':
        return (
          <StockDetailScreen
            selectedStock={selectedStock}
            setCurrentScreen={setCurrentScreen}
          />
        )
      
      case 'history':
        return <TradeHistoryScreen />
      
      case 'settings':
        return (
          <ScoreSettingsScreen
            scoreWeights={scoreWeights}
            setScoreWeights={setScoreWeights}
          />
        )
      
      case 'data':
        return <DataConnectionScreen />
      
      case 'alerts':
        return <AlertSettingsScreen />
      
      default:
        return (
          <DashboardScreen
            portfolioData={portfolioData}
            favorites={favorites}
            toggleFavorite={toggleFavorite}
          />
        )
    }
  }

  // ----------------
  // レンダリング
  // ----------------
  return (
    <div className={styles.app}>
      <Header 
        currentScreen={currentScreen} 
        setCurrentScreen={setCurrentScreen} 
      />
      
      <div className={styles.content}>
        {renderScreen()}
      </div>
    </div>
  )
}