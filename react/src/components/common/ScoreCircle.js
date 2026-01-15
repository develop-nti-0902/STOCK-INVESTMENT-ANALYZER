import React from 'react';
import styles from './ScoreCircle.module.css';

export default function ScoreCircle({ score, size = 'md' }) {
  const getColorClass = (s) => {
    if (s >= 80) return styles.scoreHigh;
    if (s >= 60) return styles.scoreMedium;
    if (s >= 40) return styles.scoreLow;
    return styles.scoreVeryLow;
  };

  return (
    <div className={`${styles.scoreCircle} ${styles[size]} ${getColorClass(score)}`}>
      {score}
    </div>
  );
}