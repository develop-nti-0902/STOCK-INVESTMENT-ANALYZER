import React, { useState } from 'react';
import { Bell, Mail, MessageSquare, Smartphone } from 'lucide-react';
import styles from './AlertSettingsScreen.module.css';

export default function AlertSettingsScreen() {
  const [alertSettings, setAlertSettings] = useState([
    {
      id: 1,
      name: '含み損益±5%超過',
      description: '保有銘柄の含み損益が±5%を超えた場合に通知',
      enabled: true,
      method: { app: true, email: true, line: false }
    },
    {
      id: 2,
      name: '貸株金利急上昇',
      description: '貸株金利が1週間で+1%以上上昇した場合に通知',
      enabled: true,
      method: { app: true, email: false, line: false }
    },
    {
      id: 3,
      name: '空売り残急増',
      description: '空売り残が前週比+10%以上増加した場合に通知',
      enabled: false,
      method: { app: true, email: false, line: false }
    },
    {
      id: 4,
      name: '決算1週間前',
      description: '保有銘柄の決算発表1週間前に通知',
      enabled: true,
      method: { app: true, email: true, line: false }
    },
    {
      id: 5,
      name: '高値・安値更新',
      description: '52週高値・安値を更新した場合に通知',
      enabled: false,
      method: { app: true, email: false, line: false }
    },
    {
      id: 6,
      name: '信用倍率急変',
      description: '信用倍率が1週間で±0.5以上変動した場合に通知',
      enabled: true,
      method: { app: true, email: false, line: false }
    },
    {
      id: 7,
      name: 'PER・PBR異常値',
      description: 'PERまたはPBRが業種平均から大きく乖離した場合に通知',
      enabled: false,
      method: { app: false, email: false, line: false }
    },
    {
      id: 8,
      name: '配当発表',
      description: '保有銘柄の配当金額が発表された場合に通知',
      enabled: true,
      method: { app: true, email: true, line: false }
    }
  ]);

  const toggleAlert = (id) => {
    setAlertSettings(prev => prev.map(alert =>
      alert.id === id ? { ...alert, enabled: !alert.enabled } : alert
    ));
  };

  const toggleMethod = (id, method) => {
    setAlertSettings(prev => prev.map(alert =>
      alert.id === id
        ? { ...alert, method: { ...alert.method, [method]: !alert.method[method] } }
        : alert
    ));
  };

  const enabledCount = alertSettings.filter(a => a.enabled).length;

  return (
    <div className={styles.container}>
      <div className={styles.mainCard}>
        <div className={styles.header}>
          <h3 className={styles.title}>
            <Bell size={28} className={styles.bellIcon} />
            アラート設定
          </h3>
          <div className={styles.counter}>
            <div className={styles.counterLabel}>有効なアラート</div>
            <div className={styles.counterValue}>{enabledCount} / {alertSettings.length}</div>
          </div>
        </div>

        <div className={styles.alertList}>
          {alertSettings.map((alert) => (
            <div key={alert.id} className={styles.alertItem}>
              <div className={styles.alertHeader}>
                <div className={styles.alertInfo}>
                  <h4 className={styles.alertName}>{alert.name}</h4>
                  <p className={styles.alertDescription}>{alert.description}</p>
                </div>
                <label className={styles.toggle}>
                  <input
                    type="checkbox"
                    className={styles.toggleInput}
                    checked={alert.enabled}
                    onChange={() => toggleAlert(alert.id)}
                  />
                  <span className={styles.toggleSlider}></span>
                  <span className={styles.toggleThumb}></span>
                </label>
              </div>

              {alert.enabled && (
                <div className={styles.methodSection}>
                  <div className={styles.methodLabel}>通知方法</div>
                  <div className={styles.methodGrid}>
                    <label className={styles.methodOption}>
                      <input
                        type="checkbox"
                        checked={alert.method.app}
                        onChange={() => toggleMethod(alert.id, 'app')}
                        className={styles.methodCheckbox}
                      />
                      <div className={styles.methodContent}>
                        <Smartphone size={18} className={styles.iconApp} />
                        <span className={styles.methodText}>アプリ内通知</span>
                      </div>
                    </label>

                    <label className={styles.methodOption}>
                      <input
                        type="checkbox"
                        checked={alert.method.email}
                        onChange={() => toggleMethod(alert.id, 'email')}
                        className={styles.methodCheckbox}
                      />
                      <div className={styles.methodContent}>
                        <Mail size={18} className={styles.iconEmail} />
                        <span className={styles.methodText}>メール</span>
                      </div>
                    </label>

                    <label className={`${styles.methodOption} ${styles.methodDisabled}`}>
                      <input
                        type="checkbox"
                        checked={alert.method.line}
                        disabled
                        className={styles.methodCheckbox}
                      />
                      <div className={styles.methodContent}>
                        <MessageSquare size={18} className={styles.iconDisabled} />
                        <span className={styles.methodTextDisabled}>LINE（準備中）</span>
                      </div>
                    </label>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className={styles.buttons}>
          <button className={styles.saveButton}>設定を保存</button>
          <button className={styles.testButton}>テスト通知を送信</button>
        </div>
      </div>

      <div className={styles.historyCard}>
        <h3 className={styles.cardTitle}>通知履歴（直近10件）</h3>
        <div className={styles.historyList}>
          <div className={`${styles.historyItem} ${styles.historyDanger}`}>
            <Bell className={styles.historyIcon} size={18} />
            <div className={styles.historyContent}>
              <div className={styles.historyMessage}>トヨタ自動車：含み損益が+5%を超えました</div>
              <div className={styles.historyTime}>2024/12/28 14:35</div>
            </div>
          </div>
          <div className={`${styles.historyItem} ${styles.historyWarning}`}>
            <Bell className={styles.historyIcon} size={18} />
            <div className={styles.historyContent}>
              <div className={styles.historyMessage}>ソフトバンクG：決算発表まであと7日</div>
              <div className={styles.historyTime}>2024/12/27 09:00</div>
            </div>
          </div>
          <div className={`${styles.historyItem} ${styles.historyOrange}`}>
            <Bell className={styles.historyIcon} size={18} />
            <div className={styles.historyContent}>
              <div className={styles.historyMessage}>キーエンス：貸株金利が+1.5%上昇</div>
              <div className={styles.historyTime}>2024/12/26 15:20</div>
            </div>
          </div>
          <div className={`${styles.historyItem} ${styles.historyInfo}`}>
            <Bell className={styles.historyIcon} size={18} />
            <div className={styles.historyContent}>
              <div className={styles.historyMessage}>ソニーG：配当金額が発表されました</div>
              <div className={styles.historyTime}>2024/12/25 16:00</div>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.hintCard}>
        <h4 className={styles.hintTitle}>💡 アラートのヒント</h4>
        <ul className={styles.hintList}>
          <li>• 重要なアラートには複数の通知方法を設定することをおすすめします</li>
          <li>• アプリ内通知は即座に確認できますが、メールは後から見返すのに便利です</li>
          <li>• テスト通知で実際の通知を確認してから運用を開始してください</li>
          <li>• アラートが多すぎる場合は、重要度の低いものをオフにすることを検討してください</li>
        </ul>
      </div>
    </div>
  );
}