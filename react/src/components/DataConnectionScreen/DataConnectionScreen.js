import React, { useState } from 'react';
import { Upload, CheckCircle } from 'lucide-react';
import styles from './DataConnectionScreen.module.css';

export default function DataConnectionScreen() {
  const [apiSettings, setApiSettings] = useState({
    stockPrice: true,
    creditInfo: true,
    shortSelling: false
  });

  const [updateFrequency, setUpdateFrequency] = useState('realtime');

  const toggleApi = (key) => {
    setApiSettings(prev => ({...prev, [key]: !prev[key]}));
  };

  const getFrequencyDescription = () => {
    const descriptions = {
      realtime: '最新の情報を常に取得します。データ使用量が多くなります。',
      '5min': '5分毎に更新します。バランスの取れた設定です。',
      '15min': '15分毎に更新します。データ使用量を抑えられます。',
      '1hour': '1時間毎に更新します。長期投資向けです。',
      daily: '1日1回の更新です。データ使用量が最小です。'
    };
    return descriptions[updateFrequency];
  };

  return (
    <div className={styles.container}>
      <div className={styles.mainCard}>
        <h3 className={styles.title}>データ連携設定</h3>
        
        <div className={styles.apiSection}>
          <h4 className={styles.apiTitle}>自動取得API設定</h4>
          <div className={styles.apiList}>
            <div className={styles.apiItem}>
              <div>
                <div className={styles.apiName}>株価データ</div>
                <div className={styles.apiDescription}>リアルタイム株価取得（遅延なし）</div>
              </div>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  className={styles.toggleInput}
                  checked={apiSettings.stockPrice}
                  onChange={() => toggleApi('stockPrice')}
                />
                <span className={styles.toggleSlider}></span>
                <span className={styles.toggleThumb}></span>
              </label>
            </div>

            <div className={styles.apiItem}>
              <div>
                <div className={styles.apiName}>信用情報</div>
                <div className={styles.apiDescription}>信用倍率・貸株金利・日証金速報</div>
              </div>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  className={styles.toggleInput}
                  checked={apiSettings.creditInfo}
                  onChange={() => toggleApi('creditInfo')}
                />
                <span className={styles.toggleSlider}></span>
                <span className={styles.toggleThumb}></span>
              </label>
            </div>

            <div className={styles.apiItem}>
              <div>
                <div className={styles.apiName}>空売り情報</div>
                <div className={styles.apiDescription}>空売り残高・比率・週次推移</div>
              </div>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  className={styles.toggleInput}
                  checked={apiSettings.shortSelling}
                  onChange={() => toggleApi('shortSelling')}
                />
                <span className={styles.toggleSlider}></span>
                <span className={styles.toggleThumb}></span>
              </label>
            </div>
          </div>
        </div>

        <div className={styles.frequencySection}>
          <h4 className={styles.frequencyTitle}>更新頻度設定</h4>
          <select
            value={updateFrequency}
            onChange={(e) => setUpdateFrequency(e.target.value)}
            className={styles.frequencySelect}
          >
            <option value="realtime">リアルタイム（1分毎）⚡ 推奨</option>
            <option value="5min">5分毎</option>
            <option value="15min">15分毎</option>
            <option value="1hour">1時間毎</option>
            <option value="daily">1日1回（朝9時）</option>
          </select>
          <p className={styles.frequencyDescription}>
            {getFrequencyDescription()}
          </p>
        </div>

        <div className={styles.buttons}>
          <button className={styles.saveButton}>設定を保存</button>
          <button className={styles.testButton}>接続テスト</button>
        </div>
      </div>

      <div className={styles.historyCard}>
        <h3 className={styles.cardTitle}>データ取得履歴</h3>
        <div className={styles.historyList}>
          <div className={styles.historyItem}>
            <div>
              <div className={styles.historyName}>株価データ</div>
              <div className={styles.historyTime}>最終更新: 2024/12/28 15:00:00</div>
            </div>
            <span className={styles.statusSuccess}>成功</span>
          </div>
          <div className={styles.historyItem}>
            <div>
              <div className={styles.historyName}>信用情報</div>
              <div className={styles.historyTime}>最終更新: 2024/12/28 15:00:00</div>
            </div>
            <span className={styles.statusSuccess}>成功</span>
          </div>
          <div className={styles.historyItem}>
            <div>
              <div className={styles.historyName}>空売り情報</div>
              <div className={styles.historyTime}>未設定</div>
            </div>
            <span className={styles.statusDisabled}>無効</span>
          </div>
        </div>
      </div>
    </div>
  );
}