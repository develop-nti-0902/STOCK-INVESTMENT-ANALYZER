import React, { useState } from 'react';
import { Upload, CheckCircle } from 'lucide-react';

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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-8 rounded-lg shadow">
        <h3 className="text-2xl font-bold mb-6">データ連携設定</h3>
        
        <div className="space-y-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-500 transition-colors">
            <Upload size={48} className="mx-auto mb-4 text-gray-400" />
            <h4 className="font-bold text-lg mb-2">CSVファイルアップロード</h4>
            <p className="text-sm text-gray-600 mb-4">
              楽天証券・SBI証券の取引履歴CSVに対応しています
            </p>
            <button className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-bold">
              ファイルを選択
            </button>
            <p className="text-xs text-gray-500 mt-3">
              対応フォーマット: CSV（Shift-JIS / UTF-8）
            </p>
          </div>

          <div className="border rounded-lg p-6 bg-gray-50">
            <h4 className="font-bold text-lg mb-4 flex items-center gap-2">
              <CheckCircle className="text-green-500" />
              証券会社対応状況
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex items-center justify-between p-3 bg-white rounded">
                <span>楽天証券</span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded text-sm font-bold">対応済み</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white rounded">
                <span>SBI証券</span>
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded text-sm font-bold">対応済み</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white rounded">
                <span>マネックス証券</span>
                <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded text-sm font-bold">準備中</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-white rounded">
                <span>松井証券</span>
                <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded text-sm font-bold">準備中</span>
              </div>
            </div>
          </div>

          <div className="border rounded-lg p-6">
            <h4 className="font-bold text-lg mb-4">自動取得API設定</h4>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div>
                  <div className="font-bold">株価データ</div>
                  <div className="text-sm text-gray-600">リアルタイム株価取得（遅延なし）</div>
                </div>
                <label className="relative inline-block w-14 h-8 cursor-pointer">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={apiSettings.stockPrice}
                    onChange={() => toggleApi('stockPrice')}
                  />
                  <span className="absolute inset-0 bg-gray-300 peer-checked:bg-blue-600 rounded-full transition"></span>
                  <span className="absolute left-1 top-1 w-6 h-6 bg-white rounded-full transition peer-checked:translate-x-6"></span>
                </label>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div>
                  <div className="font-bold">信用情報</div>
                  <div className="text-sm text-gray-600">信用倍率・貸株金利・日証金速報</div>
                </div>
                <label className="relative inline-block w-14 h-8 cursor-pointer">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={apiSettings.creditInfo}
                    onChange={() => toggleApi('creditInfo')}
                  />
                  <span className="absolute inset-0 bg-gray-300 peer-checked:bg-blue-600 rounded-full transition"></span>
                  <span className="absolute left-1 top-1 w-6 h-6 bg-white rounded-full transition peer-checked:translate-x-6"></span>
                </label>
              </div>

              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div>
                  <div className="font-bold">空売り情報</div>
                  <div className="text-sm text-gray-600">空売り残高・比率・週次推移</div>
                </div>
                <label className="relative inline-block w-14 h-8 cursor-pointer">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={apiSettings.shortSelling}
                    onChange={() => toggleApi('shortSelling')}
                  />
                  <span className="absolute inset-0 bg-gray-300 peer-checked:bg-blue-600 rounded-full transition"></span>
                  <span className="absolute left-1 top-1 w-6 h-6 bg-white rounded-full transition peer-checked:translate-x-6"></span>
                </label>
              </div>
            </div>
          </div>

          <div className="border rounded-lg p-6">
            <h4 className="font-bold text-lg mb-4">更新頻度設定</h4>
            <select
              value={updateFrequency}
              onChange={(e) => setUpdateFrequency(e.target.value)}
              className="w-full px-4 py-3 border-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
            >
              <option value="realtime">リアルタイム（1分毎）⚡ 推奨</option>
              <option value="5min">5分毎</option>
              <option value="15min">15分毎</option>
              <option value="1hour">1時間毎</option>
              <option value="daily">1日1回（朝9時）</option>
            </select>
            <p className="text-sm text-gray-600 mt-3">
              {updateFrequency === 'realtime' && '最新の情報を常に取得します。データ使用量が多くなります。'}
              {updateFrequency === '5min' && '5分毎に更新します。バランスの取れた設定です。'}
              {updateFrequency === '15min' && '15分毎に更新します。データ使用量を抑えられます。'}
              {updateFrequency === '1hour' && '1時間毎に更新します。長期投資向けです。'}
              {updateFrequency === 'daily' && '1日1回の更新です。データ使用量が最小です。'}
            </p>
          </div>

          <div className="bg-yellow-50 border-l-4 border-yellow-500 p-6 rounded">
            <h4 className="font-bold mb-2 flex items-center gap-2">
              ⚠️ 注意事項
            </h4>
            <ul className="text-sm space-y-1 text-gray-700">
              <li>• API接続には別途API利用料が発生する場合があります</li>
              <li>• リアルタイム更新は市場営業時間のみ有効です</li>
              <li>• データ取得に失敗した場合は前回のデータを表示します</li>
              <li>• CSVインポート時は既存データとの重複にご注意ください</li>
            </ul>
          </div>

          <div className="flex gap-4">
            <button className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-bold">
              設定を保存
            </button>
            <button className="px-8 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 font-bold">
              接続テスト
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white p-8 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">データ取得履歴</h3>
        <div className="space-y-2">
          <div className="flex items-center justify-between p-3 bg-green-50 rounded">
            <div>
              <div className="font-bold text-sm">株価データ</div>
              <div className="text-xs text-gray-600">最終更新: 2024/12/28 15:00:00</div>
            </div>
            <span className="px-3 py-1 bg-green-600 text-white rounded text-xs font-bold">成功</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-green-50 rounded">
            <div>
              <div className="font-bold text-sm">信用情報</div>
              <div className="text-xs text-gray-600">最終更新: 2024/12/28 15:00:00</div>
            </div>
            <span className="px-3 py-1 bg-green-600 text-white rounded text-xs font-bold">成功</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
            <div>
              <div className="font-bold text-sm">空売り情報</div>
              <div className="text-xs text-gray-600">未設定</div>
            </div>
            <span className="px-3 py-1 bg-gray-400 text-white rounded text-xs font-bold">無効</span>
          </div>
        </div>
      </div>
    </div>
  );
}
