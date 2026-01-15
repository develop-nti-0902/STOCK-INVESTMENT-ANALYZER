import React, { useState } from 'react'
import { Lock, Mail } from 'lucide-react'
import styles from './LoginScreen.module.css'

export default function LoginScreen({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // デモ用のユーザーデータ
  const demoUsers = [
    { id: 1, email: 'user1@example.com', password: 'password123', name: '山田太郎' },
    { id: 2, email: 'user2@example.com', password: 'password123', name: '佐藤花子' },
    { id: 3, email: 'demo@example.com', password: 'demo', name: 'デモユーザー' }
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    // デモ用の認証処理（実際はAPIを呼び出す）
    setTimeout(() => {
      const user = demoUsers.find(
        u => u.email === email && u.password === password
      )

      if (user) {
        // ログイン成功
        onLogin({
          id: user.id,
          name: user.name,
          email: user.email
        })
      } else {
        // ログイン失敗
        setError('メールアドレスまたはパスワードが正しくありません')
      }
      setIsLoading(false)
    }, 500)
  }

  const handleDemoLogin = () => {
    setEmail('demo@example.com')
    setPassword('demo')
    setTimeout(() => {
      onLogin({
        id: 3,
        name: 'デモユーザー',
        email: 'demo@example.com'
      })
    }, 100)
  }

  return (
    <div className={styles.container}>
      <div className={styles.loginBox}>
        <div className={styles.header}>
          <h1 className={styles.title}>株式投資管理システム</h1>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label className={styles.label}>
              <Mail size={18} />
              メールアドレス
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className={styles.input}
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label className={styles.label}>
              <Lock size={18} />
              パスワード
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className={styles.input}
              required
            />
          </div>

          {error && (
            <div className={styles.error}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className={styles.submitButton}
          >
            {isLoading ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>

        <div className={styles.divider}>
          <span>または</span>
        </div>

        <button
          onClick={handleDemoLogin}
          className={styles.demoButton}
        >
          デモアカウントでログイン
        </button>

        <div className={styles.demoInfo}>
          <p className={styles.demoInfoTitle}>デモアカウント:</p>
          <div className={styles.demoAccounts}>
            {demoUsers.map(user => (
              <div key={user.id} className={styles.demoAccount}>
                <strong>{user.email}</strong>
                <span>パスワード: {user.password}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}