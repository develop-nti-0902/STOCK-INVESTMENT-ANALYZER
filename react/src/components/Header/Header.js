import React from 'react'
import { Settings, Bell } from 'lucide-react'
import styles from './Header.module.css'

export default function Header({ currentScreen, setCurrentScreen }) {
  const menuItems = [
    { id: 'dashboard', label: 'ダッシュボード' },
    { id: 'list', label: '銘柄一覧' },
    { id: 'history', label: '取引履歴' },
  ]

  return (
    <nav className={styles.header}>
      <div className={styles.container}>
        <h1 className={styles.title}>株式投資管理システム</h1>
        <div className={styles.menu}>
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentScreen(item.id)}
              className={`${styles.menuItem} ${currentScreen === item.id ? styles.active : ''}`}
            >
              {item.label}
            </button>
          ))}
          <button
            onClick={() => setCurrentScreen('settings')}
            className={`${styles.menuItem} ${styles.iconButton} ${currentScreen === 'settings' ? styles.active : ''}`}
            title="スコア設定"
          >
            <Settings size={20} />
          </button>
          <button
            onClick={() => setCurrentScreen('data')}
            className={`${styles.menuItem} ${currentScreen === 'data' ? styles.active : ''}`}
            title="データ連携"
          >
            <span className={styles.smallText}>データ連携</span>
          </button>
          <button
            onClick={() => setCurrentScreen('alerts')}
            className={`${styles.menuItem} ${styles.iconButton} ${currentScreen === 'alerts' ? styles.active : ''}`}
            title="アラート設定"
          >
            <Bell size={20} />
          </button>
        </div>
      </div>
    </nav>
  )
}