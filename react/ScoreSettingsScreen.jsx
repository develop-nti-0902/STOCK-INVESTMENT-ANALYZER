import React from 'react';

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
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-8 rounded-lg shadow">
        <h3 className="text-2xl font-bold mb-6">スコア重み付け設定</h3>
        
        <div className="space-y-6 mb-8">
          <div>
            <div className="flex justify-between mb-2">
              <label className="font-bold text-lg">ファンダメンタル</label>
              <span className="text-2xl font-bold text-blue-600">{scoreWeights.fundamental}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={scoreWeights.fundamental}
              onChange={(e) => handleWeightChange('fundamental', e.target.value)}
              className="w-full h-3 bg-blue-200 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${scoreWeights.fundamental}%, #bfdbfe ${scoreWeights.fundamental}%, #bfdbfe 100%)`
              }}
            />
          </div>

          <div>
            <div className="flex justify-between mb-2">
              <label className="font-bold text-lg">需給</label>
              <span className="text-2xl font-bold text-green-600">{scoreWeights.supply}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={scoreWeights.supply}
              onChange={(e) => handleWeightChange('supply', e.target.value)}
              className="w-full h-3 bg-green-200 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #10b981 0%, #10b981 ${scoreWeights.supply}%, #d1fae5 ${scoreWeights.supply}%, #d1fae5 100%)`
              }}
            />
          </div>

          <div>
            <div className="flex justify-between mb-2">
              <label className="font-bold text-lg">リスク</label>
              <span className="text-2xl font-bold text-orange-600">{scoreWeights.risk}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={scoreWeights.risk}
              onChange={(e) => handleWeightChange('risk', e.target.value)}
              className="w-full h-3 bg-orange-200 rounded-lg appearance-none cursor-pointer"
              style={{
                background: `linear-gradient(to right, #f97316 0%, #f97316 ${scoreWeights.risk}%, #fed7aa ${scoreWeights.risk}%, #fed7aa 100%)`
              }}
            />
          </div>
        </div>

        <div className={`p-4 rounded mb-6 ${isValid ? 'bg-green-50 border-2 border-green-500' : 'bg-red-50 border-2 border-red-500'}`}>
          <div className="text-sm text-gray-600 mb-2">合計</div>
          <div className={`text-4xl font-bold ${isValid ? 'text-green-600' : 'text-red-600'}`}>
            {total}%
          </div>
          {!isValid && (
            <div className="text-red-600 text-sm mt-2">
              ※ 合計が100%になるように調整してください（現在: {total > 100 ? `+${total - 100}` : total - 100}%）
            </div>
          )}
          {isValid && (
            <div className="text-green-600 text-sm mt-2">
              ✓ 設定可能です
            </div>
          )}
        </div>

        <div className="flex gap-4">
          <button
            disabled={!isValid}
            className={`px-8 py-3 rounded font-bold ${
              isValid 
                ? 'bg-blue-600 text-white hover:bg-blue-700' 
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            保存
          </button>
          <button
            onClick={() => setScoreWeights({ fundamental: 40, supply: 40, risk: 20 })}
            className="px-8 py-3 bg-gray-500 text-white rounded hover:bg-gray-600 font-bold"
          >
            初期化
          </button>
        </div>
      </div>

      <div className="bg-white p-8 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">プリセット</h3>
        <div className="grid grid-cols-3 gap-4">
          <button
            onClick={() => setScoreWeights(presets.longTerm)}
            className="p-6 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
          >
            <div className="font-bold text-lg mb-3">📈 長期投資家モード</div>
            <div className="text-sm text-gray-600 mb-3">ファンダメンタル重視</div>
            <div className="text-xs space-y-1">
              <div className="flex justify-between">
                <span>ファンダ:</span>
                <span className="font-bold text-blue-600">60%</span>
              </div>
              <div className="flex justify-between">
                <span>需給:</span>
                <span className="font-bold text-green-600">20%</span>
              </div>
              <div className="flex justify-between">
                <span>リスク:</span>
                <span className="font-bold text-orange-600">20%</span>
              </div>
            </div>
          </button>

          <button
            onClick={() => setScoreWeights(presets.shortTerm)}
            className="p-6 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
          >
            <div className="font-bold text-lg mb-3">⚡ 短期トレーダーモード</div>
            <div className="text-sm text-gray-600 mb-3">需給重視</div>
            <div className="text-xs space-y-1">
              <div className="flex justify-between">
                <span>ファンダ:</span>
                <span className="font-bold text-blue-600">20%</span>
              </div>
              <div className="flex justify-between">
                <span>需給:</span>
                <span className="font-bold text-green-600">60%</span>
              </div>
              <div className="flex justify-between">
                <span>リスク:</span>
                <span className="font-bold text-orange-600">20%</span>
              </div>
            </div>
          </button>

          <button
            onClick={() => setScoreWeights(presets.dividend)}
            className="p-6 border-2 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all"
          >
            <div className="font-bold text-lg mb-3">💰 配当投資モード</div>
            <div className="text-sm text-gray-600 mb-3">バランス型</div>
            <div className="text-xs space-y-1">
              <div className="flex justify-between">
                <span>ファンダ:</span>
                <span className="font-bold text-blue-600">50%</span>
              </div>
              <div className="flex justify-between">
                <span>需給:</span>
                <span className="font-bold text-green-600">30%</span>
              </div>
              <div className="flex justify-between">
                <span>リスク:</span>
                <span className="font-bold text-orange-600">20%</span>
              </div>
            </div>
          </button>
        </div>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-6 rounded">
        <h4 className="font-bold mb-2">💡 使い方のヒント</h4>
        <ul className="text-sm space-y-1 text-gray-700">
          <li>• <strong>ファンダメンタル:</strong> 企業の財務健全性や成長性を重視する場合は高めに設定</li>
          <li>• <strong>需給:</strong> 信用取引や空売り動向を重視する場合は高めに設定</li>
          <li>• <strong>リスク:</strong> ボラティリティや決算リスクを重視する場合は高めに設定</li>
          <li>• 合計が100%になるように調整してください</li>
        </ul>
      </div>
    </div>
  );
}
