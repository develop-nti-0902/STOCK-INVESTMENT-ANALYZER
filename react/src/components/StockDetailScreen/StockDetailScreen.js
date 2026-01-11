import React from 'react'
import styles from './StockDetailScreen.module.css'

export default function StockDetailScreen({ stock, setCurrentScreen }) {
	if (!stock) {
		return (
			<div className={styles.container}>
				<p>銘柄が選択されていません。</p>
				<button onClick={() => setCurrentScreen('list')} className={styles.backButton}>一覧に戻る</button>
			</div>
		)
	}

	return (
		<div className={styles.container}>
			<button onClick={() => setCurrentScreen('list')} className={styles.backButton}>一覧に戻る</button>
			<h2 className={styles.title}>{stock.code} {stock.name}</h2>
			<div className={styles.detailGrid}>
				<div>セクター: {stock.sector}</div>
				<div>現在値: ¥{stock.price.toLocaleString()}</div>
				<div>変動率: {stock.change}%</div>
				<div>ファンダ: {stock.fundamental}</div>
				<div>需給: {stock.supply}</div>
				<div>リスク: {stock.risk}</div>
				<div>総合: {stock.overall}</div>
			</div>
		</div>
	)
}
