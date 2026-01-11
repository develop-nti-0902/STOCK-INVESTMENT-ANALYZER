import React from 'react';
import styles from './ScoreSettingsScreen.module.css';

export default function ScoreSettingsScreen({ scoreWeights, setScoreWeights }) {
  const handleWeightChange = (key, value) => {
    setScoreWeights({...scoreWeights, [key]: parseInt(value)});
  };

  const presets = {
    longTerm: { fundamental: 60, supply: 20, risk: 20 },
    shortTerm: { fundamental: 20, supply: 60, risk: 20 },
    dividend: { fundamental: 50, supply: 30, risk: 20 }
  };

  const total = scoreWeights.fundamental + scoreWeights.supply + scoreWeights.risk;
  const isValid = total === 100;

  return (
    <div className={styles.container}>
      <div className={styles.settingsCard}>
        <h3 className={styles.title}>スコア重み付け設定</h3>
        
        <div className={styles.sliderSection}>
          <div className={styles.sliderGroup}>
            <div className={styles.sliderHeader}>
              <label className={styles.sliderLabel}>ファンダメンタル</label>
              <span className={styles.sliderValue}>{scoreWeights.fundamental}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={scoreWeights.fundamental}
              onChange={(e) => handleWeightChange('fundamental', e.target.value)}
              className={styles.slider}
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${scoreWeights.fundamental}%, #bfdbfe ${scoreWeights.fundamental}%, #bfdbfe 100%)`
              }}
            />
          </div>

          <div className={styles.sliderGroup}>
            <div className={styles.sliderHeader}>
              <label className={styles.sliderLabel}>需給</label>
              <span className={`${styles.sliderValue} ${styles.valueGreen}`}>{scoreWeights.supply}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={scoreWeights.supply}
              onChange={(e) => handleWeightChange('supply', e.target.value)}
              className={styles.slider}
              style={{
                background: `linear-gradient(to right, #10b981 0%, #10b981 ${scoreWeights.supply}%, #d1fae5 ${scoreWeights.supply}%, #d1fae5 100%)`
              }}
            />
          </div>

          <div className={styles.sliderGroup}>
            <div className={styles.sliderHeader}>
              <label className={styles.sliderLabel}>リスク</label>
              <span className={`${styles.sliderValue} ${styles.valueOrange}`}>{scoreWeights.risk}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={scoreWeights.risk}
              onChange={(e) => handleWeightChange('risk', e.target.value)}
              className={styles.slider}
              style={{
                background: `linear-gradient(to right, #f97316 0%, #f97316 ${scoreWeights.risk}%, #fed7aa ${scoreWeights.risk}%, #fed7aa 100%)`
              }}
            />
          </div>
        </div>

        <div className={`${styles.totalBox} ${isValid ? styles.totalValid : styles.totalInvalid}`}>
          <div className={styles.totalLabel}>合計</div>
          <div className={styles.totalValue}>
            {total}%
          </div>
          {!isValid && (
            <div className={styles.errorMessage}>
              ※ 合計が100%になるように調整してください（現在: {total > 100 ? `+${total - 100}` : total - 100}%）
            </div>
          )}
          {isValid && (
            <div className={styles.successMessage}>
              ✓ 設定可能です
            </div>
          )}
        </div>

        <div className={styles.buttons}>
          <button
            disabled={!isValid}
            className={`${styles.saveButton} ${!isValid ? styles.buttonDisabled : ''}`}
          >
            保存
          </button>
          <button
            onClick={() => setScoreWeights({ fundamental: 40, supply: 40, risk: 20 })}
            className={styles.resetButton}
          >
            初期化
          </button>
        </div>
      </div>

      <div className={styles.presetsCard}>
        <h3 className={styles.cardTitle}>プリセット</h3>
        <div className={styles.presetGrid}>
          <button
            onClick={() => setScoreWeights(presets.longTerm)}
            className={styles.presetButton}
          >
            <div className={styles.presetTitle}>📈 長期投資家モード</div>
            <div className={styles.presetDescription}>ファンダメンタル重視</div>
            <div className={styles.presetValues}>
              <div className={styles.presetRow}>
                <span>ファンダ:</span>
                <span className={styles.presetValueBlue}>60%</span>
              </div>
              <div className={styles.presetRow}>
                <span>需給:</span>
                <span className={styles.presetValueGreen}>20%</span>
              </div>
              <div className={styles.presetRow}>
                <span>リスク:</span>
                <span className={styles.presetValueOrange}>20%</span>
              </div>
            </div>
          </button>

          <button
            onClick={() => setScoreWeights(presets.shortTerm)}
            className={styles.presetButton}
          >
            <div className={styles.presetTitle}>⚡ 短期トレーダーモード</div>
            <div className={styles.presetDescription}>需給重視</div>
            <div className={styles.presetValues}>
              <div className={styles.presetRow}>
                <span>ファンダ:</span>
                <span className={styles.presetValueBlue}>20%</span>
              </div>
              <div className={styles.presetRow}>
                <span>需給:</span>
                <span className={styles.presetValueGreen}>60%</span>
              </div>
              <div className={styles.presetRow}>
                <span>リスク:</span>
                <span className={styles.presetValueOrange}>20%</span>
              </div>
            </div>
          </button>

          <button
            onClick={() => setScoreWeights(presets.dividend)}
            className={styles.presetButton}
          >
            <div className={styles.presetTitle}>💰 配当投資モード</div>
            <div className={styles.presetDescription}>バランス型</div>
            <div className={styles.presetValues}>
              <div className={styles.presetRow}>
                <span>ファンダ:</span>
                <span className={styles.presetValueBlue}>50%</span>
              </div>
              <div className={styles.presetRow}>
                <span>需給:</span>
                <span className={styles.presetValueGreen}>30%</span>
              </div>
              <div className={styles.presetRow}>
                <span>リスク:</span>
                <span className={styles.presetValueOrange}>20%</span>
              </div>
            </div>
          </button>
        </div>
      </div>

      <div className={styles.hintCard}>
        <h4 className={styles.hintTitle}>💡 使い方のヒント</h4>
        <ul className={styles.hintList}>
          <li>• <strong>ファンダメンタル:</strong> 企業の財務健全性や成長性を重視する場合は高めに設定</li>
          <li>• <strong>需給:</strong> 信用取引や空売り動向を重視する場合は高めに設定</li>
          <li>• <strong>リスク:</strong> ボラティリティや決算リスクを重視する場合は高めに設定</li>
          <li>• 合計が100%になるように調整してください</li>
        </ul>
      </div>
    </div>
  );
}