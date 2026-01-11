import React, { useState } from 'react';
import { Star, Download, ChevronRight } from 'lucide-react';

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

export default function StockListScreen({ stockList, favorites, toggleFavorite, setSelectedStock, setCurrentScreen }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSector, setFilterSector] = useState('');
  const [sortBy, setSortBy] = useState('overall');
  const [sortDir, setSortDir] = useState('desc');

  const filteredStocks = stockList
    .filter(s => !searchTerm || s.name.includes(searchTerm) || s.code.includes(searchTerm))
    .filter(s => !filterSector || s.sector === filterSector)
    .sort((a, b) => {
      const mult = sortDir === 'asc' ? 1 : -1;
      return (a[sortBy] - b[sortBy]) * mult;
    });

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(key);
      setSortDir('desc');
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-white p-4 rounded-lg shadow flex gap-4">
        <input
          type="text"
          placeholder="銘柄名・コードで検索"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={filterSector}
          onChange={(e) => setFilterSector(e.target.value)}
          className="px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">全セクター</option>
          <option value="輸送用機器">輸送用機器</option>
          <option value="情報・通信業">情報・通信業</option>
          <option value="電気機器">電気機器</option>
          <option value="化学">化学</option>
          <option value="銀行業">銀行業</option>
        </select>
        <button className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2">
          <Download size={18} />
          CSV
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-700 text-white">
            <tr>
              <th className="px-4 py-3 text-left">⭐</th>
              <th className="px-4 py-3 text-left cursor-pointer hover:bg-gray-600" onClick={() => handleSort('code')}>
                銘柄 {sortBy === 'code' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-right cursor-pointer hover:bg-gray-600" onClick={() => handleSort('price')}>
                現在値 {sortBy === 'price' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-right cursor-pointer hover:bg-gray-600" onClick={() => handleSort('change')}>
                変動率 {sortBy === 'change' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-center cursor-pointer hover:bg-gray-600" onClick={() => handleSort('fundamental')}>
                ファンダ {sortBy === 'fundamental' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-center cursor-pointer hover:bg-gray-600" onClick={() => handleSort('supply')}>
                需給 {sortBy === 'supply' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-center cursor-pointer hover:bg-gray-600" onClick={() => handleSort('risk')}>
                リスク {sortBy === 'risk' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-center cursor-pointer hover:bg-gray-600" onClick={() => handleSort('overall')}>
                総合 {sortBy === 'overall' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th className="px-4 py-3 text-left">セクター</th>
              <th className="px-4 py-3 text-center">詳細</th>
            </tr>
          </thead>
          <tbody>
            {filteredStocks.map((stock) => (
              <tr key={stock.code} className="border-b hover:bg-blue-50">
                <td className="px-4 py-3">
                  <button onClick={() => toggleFavorite(stock.code)}>
                    <Star size={18} className={favorites.includes(stock.code) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'} />
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="font-bold">{stock.code}</div>
                  <div className="text-xs text-gray-500">{stock.name}</div>
                </td>
                <td className="px-4 py-3 text-right font-bold">¥{stock.price.toLocaleString()}</td>
                <td className={`px-4 py-3 text-right font-bold ${stock.change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {stock.change > 0 ? '+' : ''}{stock.change}%
                </td>
                <td className="px-4 py-3 text-center"><ScoreCircle score={stock.fundamental} size="sm" /></td>
                <td className="px-4 py-3 text-center"><ScoreCircle score={stock.supply} size="sm" /></td>
                <td className="px-4 py-3 text-center"><ScoreCircle score={stock.risk} size="sm" /></td>
                <td className="px-4 py-3 text-center"><ScoreCircle score={stock.overall} /></td>
                <td className="px-4 py-3 text-xs">{stock.sector}</td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => { setSelectedStock(stock); setCurrentScreen('detail'); }}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    <ChevronRight size={20} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="bg-white p-4 rounded-lg shadow flex justify-between items-center">
        <div className="text-sm text-gray-600">
          全{filteredStocks.length}件を表示
        </div>
        <div className="text-sm text-gray-600">
          ソート: {sortBy === 'code' ? '銘柄コード' : sortBy === 'price' ? '現在値' : sortBy === 'change' ? '変動率' : sortBy === 'fundamental' ? 'ファンダ' : sortBy === 'supply' ? '需給' : sortBy === 'risk' ? 'リスク' : '総合スコア'} ({sortDir === 'asc' ? '昇順' : '降順'})
        </div>
      </div>
    </div>
  );
}
