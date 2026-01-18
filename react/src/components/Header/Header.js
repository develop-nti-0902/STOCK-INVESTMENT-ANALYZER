import React, { useState } from 'react'
import { Settings, Bell, User, LogOut, ChevronDown } from 'lucide-react'
import styles from './Header.module.css'

export default function Header({ currentScreen, setCurrentScreen, currentUser, onLogout }) {
  const [showUserMenu, setShowUserMenu] = useState(false)

  const menuItems = [
    { id: 'dashboard', label: 'ダッシュボード' },
    { id: 'list', label: '銘柄一覧' },
    { id: 'history', label: '取引履歴' },
  ]

  const handleLogout = () => {
    setShowUserMenu(false)
    if (onLogout) {
      onLogout()
    }
  }

  return (
    <nav className={styles.header}>
      <div className={styles.container}>
        <h1 className={styles.title}>
          株式投資管理<br />
          システム
        </h1>

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

          {/* ユーザーメニュー */}
          <div className={styles.userMenuContainer}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className={styles.userMenuButton}
            >
              <User size={20} />
              <span className={styles.userName}>{currentUser?.name || 'ゲスト'}</span>
              <ChevronDown size={16} className={showUserMenu ? styles.chevronUp : ''} />
            </button>

            {showUserMenu && (
              <div className={styles.userMenuDropdown}>
                <div className={styles.userInfo}>
                  <div className={styles.userInfoName}>{currentUser?.name || 'ゲスト'}</div>
                  <div className={styles.userInfoEmail}>{currentUser?.email || ''}</div>
                </div>
                <div className={styles.userMenuDivider}></div>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    setCurrentScreen('profile')
                  }}
                  className={styles.userMenuItem}
                >
                  <User size={18} />
                  プロフィール
                </button>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    setCurrentScreen('settings')
                  }}
                  className={styles.userMenuItem}
                >
                  <Settings size={18} />
                  設定
                </button>
                <div className={styles.userMenuDivider}></div>
                <button
                  onClick={handleLogout}
                  className={`${styles.userMenuItem} ${styles.logoutButton}`}
                >
                  <LogOut size={18} />
                  ログアウト
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* オーバーレイ（メニュー外クリックで閉じる） */}
      {showUserMenu && (
        <div
          className={styles.overlay}
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </nav>
  )
}