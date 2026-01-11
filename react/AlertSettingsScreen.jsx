import React, { useState } from 'react';
import { Bell, Mail, MessageSquare, Smartphone } from 'lucide-react';

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
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-8 rounded-lg shadow">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <Bell size={28} className="text-blue-600" />
            アラート設定
          </h3>
          <div className="text-right">
            <div className="text-sm text-gray-600">有効なアラート</div>
            <div className="text-3xl font-bold text-blue-600">{enabledCount} / {alertSettings.length}</div>
          </div>
        </div>

        <div className="space-y-4">
          {alertSettings.map((alert) => (
            <div key={alert.id} className="border-2 rounded-lg p-6 hover:border-blue-300 transition-colors">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h4 className="font-bold text-lg mb-1">{alert.name}</h4>
                  <p className="text-sm text-gray-600">{alert.description}</p>
                </div>
                <label className="relative inline-block w-14 h-8 cursor-pointer ml-4">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={alert.enabled}
                    onChange={() => toggleAlert(alert.id)}
                  />
                  <span className="absolute inset-0 bg-gray-300 peer-checked:bg-blue-600 rounded-full transition"></span>
                  <span className="absolute left-1 top-1 w-6 h-6 bg-white rounded-full transition peer-checked:translate-x-6"></span>
                </label>
              </div>

              {alert.enabled && (
                <div className="border-t pt-4">
                  <div className="text-sm font-bold text-gray-700 mb-3">通知方法</div>
                  <div className="grid grid-cols-3 gap-3">
                    <label className="flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={alert.method.app}
                        onChange={() => toggleMethod(alert.id, 'app')}
                        className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="flex items-center gap-2">
                        <Smartphone size={18} className="text-blue-600" />
                        <span className="text-sm font-medium">アプリ内通知</span>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-3 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={alert.method.email}
                        onChange={() => toggleMethod(alert.id, 'email')}
                        className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                      />
                      <div className="flex items-center gap-2">
                        <Mail size={18} className="text-green-600" />
                        <span className="text-sm font-medium">メール</span>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-3 border-2 rounded-lg cursor-not-allowed bg-gray-50">
                      <input
                        type="checkbox"
                        checked={alert.method.line}
                        disabled
                        className="w-5 h-5 text-gray-400 border-gray-300 rounded"
                      />
                      <div className="flex items-center gap-2">
                        <MessageSquare size={18} className="text-gray-400" />
                        <span className="text-sm font-medium text-gray-400">LINE（準備中）</span>
                      </div>
                    </label>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 flex gap-4">
          <button className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-bold">
            設定を保存
          </button>
          <button className="px-8 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 font-bold">
            テスト通知を送信
          </button>
        </div>
      </div>

      <div className="bg-white p-8 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">通知履歴（直近10件）</h3>
        <div className="space-y-2">
          <div className="flex items-start gap-3 p-4 bg-red-50 border-l-4 border-red-500 rounded">
            <Bell className="text-red-500 mt-1" size={18} />
            <div className="flex-1">
              <div className="font-bold text-sm">トヨタ自動車：含み損益が+5%を超えました</div>
              <div className="text-xs text-gray-600">2024/12/28 14:35</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-yellow-50 border-l-4 border-yellow-500 rounded">
            <Bell className="text-yellow-500 mt-1" size={18} />
            <div className="flex-1">
              <div className="font-bold text-sm">ソフトバンクG：決算発表まであと7日</div>
              <div className="text-xs text-gray-600">2024/12/27 09:00</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-orange-50 border-l-4 border-orange-500 rounded">
            <Bell className="text-orange-500 mt-1" size={18} />
            <div className="flex-1">
              <div className="font-bold text-sm">キーエンス：貸株金利が+1.5%上昇</div>
              <div className="text-xs text-gray-600">2024/12/26 15:20</div>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-blue-50 border-l-4 border-blue-500 rounded">
            <Bell className="text-blue-500 mt-1" size={18} />
            <div className="flex-1">
              <div className="font-bold text-sm">ソニーG：配当金額が発表されました</div>
              <div className="text-xs text-gray-600">2024/12/25 16:00</div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border-l-4 border-blue-500 p-6 rounded">
        <h4 className="font-bold mb-2">💡 アラートのヒント</h4>
        <ul className="text-sm space-y-1 text-gray-700">
          <li>• 重要なアラートには複数の通知方法を設定することをおすすめします</li>
          <li>• アプリ内通知は即座に確認できますが、メールは後から見返すのに便利です</li>
          <li>• テスト通知で実際の通知を確認してから運用を開始してください</li>
          <li>• アラートが多すぎる場合は、重要度の低いものをオフにすることを検討してください</li>
        </ul>
      </div>
    </div>
  );
}
