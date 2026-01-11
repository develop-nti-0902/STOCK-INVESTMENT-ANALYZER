import React from 'react';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const ScoreCircle = ({ score, size = 'md' }) => {
  const sizeClass = size === 'sm' ? 'w-8 h-8 text-xs' : size === 'lg' ? 'w-16 h-16 text-2xl' : 'w-12 h-12 text-lg';
  const getColor = (s) => {
    if (s >= 80) return 'bg-green-500';
    if (s >= 60) return 'bg-blue-500';
    if (s >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };
  return (
    <div className={`${sizeClass} ${getColor(score)} rounded-full flex items-center justify-center text-white font-bold`}>
      {score}
    </div>
  );
};

export default function StockDetailScreen({ selectedStock, setCurrentScreen }) {
  if (!selectedStock) {
    return (
      <div className="bg-white p-8 rounded-lg shadow text-center">
        <p className="text-gray-500">銘柄が選択されていません</p>
        <button
          onClick={() => setCurrentScreen('list')}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          銘柄一覧に戻る
        </button>
      </div>
    );
  }

  const detailRadarData = [
    { metric: 'ファンダ', value: selectedStock.fundamental },
    { metric: '需給', value: selectedStock.supply },
    { metric: 'リスク', value: selectedStock.risk }
  ];

  const fundamentalDetails = [
    { label: '売上成長率', value: 12.5, unit: '%', score: 85 },
    { label: 'EPS成長率', value: 18.3, unit: '%', score: 88 },
    { label: '営業CF', value: 2500, unit: '億円', score: 82 },
    { label: '自己資本比率', value: 45.2, unit: '%', score: 78 },
    { label: 'ROE', value: selectedStock.roe, unit: '%', score: 75 },
    { label: '配当性向', value: 32.5, unit: '%', score: 80 }
  ];

  const supplyDetails = [
    { label: '信用倍率', value: 1.23, score: 72 },
    { label: '空売り残', value: 35.6, unit: '%', score: 65 },
    { label: '貸株金利', value: 2.8, unit: '%', score: 70 },
    { label: '出来高推移', value: '増加傾向', score: 78 }
  ];

  const riskDetails = [
    { label: 'ボラティリティ', value: 18.5, unit: '%', score: selectedStock.risk },
    { label: '決算まで', value: 3, unit: '日', score: 45 },
    { label: '流動性', value: '高', score: 85 },
    { label: '材料出尽くし', value: '低', score: 75 }
  ];

  const priceHistory = [
    { date: '11/28', price: 2680 },
    { date: '12/05', price: 2720 },
    { date: '12/12', price: 2650 },
    { date: '12/19', price: 2780 },
    { date: '12/26', price: selectedStock.price }
  ];

  return (
    <div className="space-y-6">
      <button
        onClick={() => setCurrentScreen('list')}
        className="text-blue-600 hover:text-blue-800 flex items-center gap-2"
      >
        ← 一覧に戻る
      </button>

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-3xl font-bold">{selectedStock.code} {selectedStock.name}</h2>
            <div className="text-sm text-gray-500 mt-1">{selectedStock.sector}</div>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold">¥{selectedStock.price.toLocaleString()}</div>
            <div className={`text-lg font-bold ${selectedStock.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {selectedStock.change > 0 ? '+' : ''}{selectedStock.change}%
            </div>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mt-6">
          <div>
            <div className="text-sm text-gray-500">時価総額</div>
            <div className="text-lg font-bold">¥{(selectedStock.marketCap / 100000000).toFixed(0)}兆円</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">PER</div>
            <div className="text-lg font-bold">{selectedStock.per}倍</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">PBR</div>
            <div className="text-lg font-bold">{selectedStock.pbr}倍</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">ROE</div>
            <div className="text-lg font-bold">{selectedStock.roe}%</div>
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">株価チャート</h3>
        <div className="flex gap-2 mb-4">
          {['1M', '3M', '6M', '1Y', 'MAX'].map(period => (
            <button key={period} className="px-4 py-1 border rounded hover:bg-gray-100">
              {period}
            </button>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={priceHistory}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">スコア可視化</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={detailRadarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" />
              <PolarRadiusAxis angle={90} domain={[0, 100]} />
              <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
            </RadarChart>
          </ResponsiveContainer>
          <div className="flex justify-around mt-4">
            <div className="text-center">
              <ScoreCircle score={selectedStock.fundamental} />
              <div className="text-xs mt-1">ファンダ</div>
            </div>
            <div className="text-center">
              <ScoreCircle score={selectedStock.supply} />
              <div className="text-xs mt-1">需給</div>
            </div>
            <div className="text-center">
              <ScoreCircle score={selectedStock.risk} />
              <div className="text-xs mt-1">リスク</div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-3">ファンダメンタル詳細</h3>
          <div className="space-y-2">
            {fundamentalDetails.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">{item.label}</span>
                <div className="flex items-center gap-3">
                  <span className="font-bold">{item.value}{item.unit || ''}</span>
                  <ScoreCircle score={item.score} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-3">需給詳細</h3>
          <div className="space-y-2">
            {supplyDetails.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">{item.label}</span>
                <div className="flex items-center gap-3">
                  <span className="font-bold">{item.value}{item.unit || ''}</span>
                  <ScoreCircle score={item.score} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-3">リスク詳細</h3>
          <div className="space-y-2">
            {riskDetails.map((item, idx) => (
              <div key={idx} className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">{item.label}</span>
                <div className="flex items-center gap-3">
                  <span className="font-bold">{item.value}{item.unit || ''}</span>
                  <ScoreCircle score={item.score} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
