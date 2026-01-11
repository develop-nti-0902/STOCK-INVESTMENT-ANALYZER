import React from 'react';
import { Settings, Bell } from 'lucide-react';

export default function Header({ currentScreen, setCurrentScreen }) {
  const menuItems = [
    { id: 'dashboard', label: 'ダッシュボード' },
    { id: 'list', label: '銘柄一覧' },
    { id: 'history', label: '取引履歴' },
  ];

  return (
    <nav className="bg-gray-800 text-white p-4 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <h1 className="text-2xl font-bold">株式投資管理システム</h1>
        <div className="flex gap-4">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setCurrentScreen(item.id)}
              className={`px-4 py-2 rounded transition-colors ${
                currentScreen === item.id ? 'bg-blue-600' : 'hover:bg-gray-700'
              }`}
            >
              {item.label}
            </button>
          ))}
          <button
            onClick={() => setCurrentScreen('settings')}
            className={`px-4 py-2 rounded transition-colors ${
              currentScreen === 'settings' ? 'bg-blue-600' : 'hover:bg-gray-700'
            }`}
            title="スコア設定"
          >
            <Settings size={20} />
          </button>
          <button
            onClick={() => setCurrentScreen('data')}
            className={`px-4 py-2 rounded transition-colors ${
              currentScreen === 'data' ? 'bg-blue-600' : 'hover:bg-gray-700'
            }`}
            title="データ連携"
          >
            <span className="text-sm">データ連携</span>
          </button>
          <button
            onClick={() => setCurrentScreen('alerts')}
            className={`px-4 py-2 rounded transition-colors ${
              currentScreen === 'alerts' ? 'bg-blue-600' : 'hover:bg-gray-700'
            }`}
            title="アラート設定"
          >
            <Bell size={20} />
          </button>
        </div>
      </div>
    </nav>
  );
}
