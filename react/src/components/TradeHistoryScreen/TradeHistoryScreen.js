import React, { useState } from 'react';
import { Upload } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import styles from './TradeHistoryScreen.module.css';

export default function TradeHistoryScreen() {
  const [tradeForm, setTradeForm] = useState({
    type: '買',
    code: '',
    quantity: '',
    price: '',
    fee: '',
    account: 'NISA'
  });

  const tradeHistory = [
    { date: '2024/12/15', type: '買', code: '7203', name: 'トヨタ自動車', quantity: 100, price: 2650, fee: 500, account: 'NISA' },
    { date: '2024/12/10', type: '売', code: '9984', name: 'ソフトバンクG', quantity: 50, price: 8100, fee: 450, account: '特定' },
    { date: '2024/12/05', type: '買', code: '6758', name: 'ソニーG', quantity: 50, price: 13000, fee: 600, account: 'NISA' },
    { date: '2024/11/28', type: '買', code: '6861', name: 'キーエンス', quantity: 10, price: 65000, fee: 700, account: '特定' },
    { date: '2024/11/20', type: '売', code: '4063', name: '信越化学', quantity: 100, price: 4350, fee: 400, account: '特定' }
  ];

  const monthlyPL = [
    { month: '1月', pl: 45000 },
    { month: '2月', pl: -12000 },
    { month: '3月', pl: 78000 },
    { month: '4月', pl: 123000 },
    { month: '5月', pl: 56000 },
    { month: '6月', pl: 89000 },
    { month: '7月', pl: 102000 },
    { month: '8月', pl: -34000 },
    { month: '9月', pl: 156000 },
    { month: '10月', pl: 78000 },
    { month: '11月', pl: 145000 },
    { month: '12月', pl: 234000 }
  ];

  const handleInputChange = (field, value) => {
    setTradeForm(prev => ({...prev, [field]: value}));
  };

  const handleSubmit = () => {
    console.log('取引登録:', tradeForm);
    setTradeForm({
      type: '買',
      code: '',
      quantity: '',
      price: '',
      fee: '',
      account: 'NISA'
    });
  };

  const totalPL = monthlyPL.reduce((sum, m) => sum + m.pl, 0);
  const plusMonths = monthlyPL.filter(m => m.pl > 0).length;
  const minusMonths = monthlyPL.filter(m => m.pl < 0).length;

  return (
    <div className={styles.container}>
      <div className={styles.formCard}>
        <h3 className={styles.cardTitle}>取引入力</h3>
        <div className={styles.formGrid}>
          <div className={styles.formGroup}>
            <label className={styles.label}>売買区分</label>
            <select
              value={tradeForm.type}
              onChange={(e) => handleInputChange('type', e.target.value)}
              className={styles.select}
            >
              <option>買</option>
              <option>売</option>
            </select>
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>銘柄コード</label>
            <input
              type="text"
              value={tradeForm.code}
              onChange={(e) => handleInputChange('code', e.target.value)}
              className={styles.input}
              placeholder="7203"
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>数量</label>
            <input
              type="number"
              value={tradeForm.quantity}
              onChange={(e) => handleInputChange('quantity', e.target.value)}
              className={styles.input}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>取得単価</label>
            <input
              type="number"
              value={tradeForm.price}
              onChange={(e) => handleInputChange('price', e.target.value)}
              className={styles.input}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>手数料</label>
            <input
              type="number"
              value={tradeForm.fee}
              onChange={(e) => handleInputChange('fee', e.target.value)}
              className={styles.input}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>口座区分</label>
            <select
              value={tradeForm.account}
              onChange={(e) => handleInputChange('account', e.target.value)}
              className={styles.select}
            >
              <option>NISA</option>
              <option>特定</option>
              <option>一般</option>
            </select>
          </div>
        </div>
        <div className={styles.formButtons}>
          <button onClick={handleSubmit} className={styles.submitButton}>
            登録
          </button>
          <button className={styles.importButton}>
            <Upload size={18} />
            CSVインポート
          </button>
        </div>
      </div>

      <div className={styles.chartCard}>
        <h3 className={styles.cardTitle}>月次損益推移</h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={monthlyPL}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="pl" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
        <div className={styles.summaryGrid}>
          <div className={styles.summaryCard}>
            <div className={styles.summaryLabel}>年間合計</div>
            <div className={styles.summaryValue}>
              +¥{totalPL.toLocaleString()}
            </div>
          </div>
          <div className={`${styles.summaryCard} ${styles.summaryPositive}`}>
            <div className={styles.summaryLabel}>プラス月</div>
            <div className={styles.summaryValue}>
              {plusMonths}ヶ月
            </div>
          </div>
          <div className={`${styles.summaryCard} ${styles.summaryNegative}`}>
            <div className={styles.summaryLabel}>マイナス月</div>
            <div className={styles.summaryValue}>
              {minusMonths}ヶ月
            </div>
          </div>
        </div>
      </div>

      <div className={styles.historyCard}>
        <h3 className={styles.cardTitle}>取引履歴</h3>
        <div className={styles.tableContainer}>
          <table className={styles.table}>
            <thead className={styles.tableHead}>
              <tr>
                <th className={styles.th}>日付</th>
                <th className={styles.th}>区分</th>
                <th className={styles.th}>銘柄</th>
                <th className={`${styles.th} ${styles.alignRight}`}>数量</th>
                <th className={`${styles.th} ${styles.alignRight}`}>単価</th>
                <th className={`${styles.th} ${styles.alignRight}`}>手数料</th>
                <th className={`${styles.th} ${styles.alignRight}`}>合計</th>
                <th className={styles.th}>口座</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.map((trade, idx) => (
                <tr key={idx} className={styles.tableRow}>
                  <td className={`${styles.td} ${styles.dateCell}`}>{trade.date}</td>
                  <td className={styles.td}>
                    <span className={trade.type === '買' ? styles.badgeBuy : styles.badgeSell}>
                      {trade.type}
                    </span>
                  </td>
                  <td className={styles.td}>
                    <div className={styles.stockCode}>{trade.code}</div>
                    <div className={styles.stockName}>{trade.name}</div>
                  </td>
                  <td className={`${styles.td} ${styles.alignRight}`}>{trade.quantity}株</td>
                  <td className={`${styles.td} ${styles.alignRight}`}>¥{trade.price.toLocaleString()}</td>
                  <td className={`${styles.td} ${styles.alignRight}`}>¥{trade.fee.toLocaleString()}</td>
                  <td className={`${styles.td} ${styles.alignRight} ${styles.total}`}>
                    ¥{(trade.quantity * trade.price + trade.fee).toLocaleString()}
                  </td>
                  <td className={`${styles.td} ${styles.accountCell}`}>{trade.account}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}