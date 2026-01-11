import React from 'react';
import { TrendingUp, AlertTriangle, Star } from 'lucide-react';
import { PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip, ResponsiveContainer } from 'recharts';

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

const OverallScoreBadge = ({ score }) => {
  const badges = { '◎': 'bg-green-600', '○': 'bg-blue-600', '△': 'bg-yellow-600', '×': 'bg-red-600' };
  return (
    <span className={`${badges[score]} text-white px-4 py-2 rounded-full text-2xl font-bold`}>
      {score}
    </span>
  );
};

export default function DashboardScreen({ portfolioData, favorites, toggleFavorite }) {
  const sectorData = [
    { name: '輸送用機器', value: 30, color: '#3b82f6' },
    { name: '情報・通信業', value: 25, color: '#10b981' },
    { name: '電気機器', value: 30, color: '#f59e0b' },
    { name: '化学', value: 15, color: '#8b5cf6' }
  ];

  const radarData = [
    { metric: '成長性', value: 85 },
    { metric: '収益性', value: 78 },
    { metric: '安定性', value: 82 },
    { metric: '需給', value: 72 },
    { metric: '流動性', value: 88 }
  ];

  const alerts = [
    { type: 'warning', message: 'トヨタ自動車：決算発表まであと3日', priority: 'high' },
    { type: 'danger', message: 'ソフトバンクG：貸株金利が2.5%→4.2%に上昇', priority: 'high' },
    { type: 'info', message: 'キーエンス：空売り残が前週比+15%', priority: 'medium' }
  ];

  const recentNews = [
    { date: '2024/12/28', title: 'トヨタ、EV新戦略発表へ', sentiment: 'positive' },
    { date: '2024/12/27', title: 'ソフトバンクG、AI投資拡大', sentiment: 'positive' },
    { date: '2024/12/26', title: '半導体関連に注目集まる', sentiment: 'neutral' }
  ];

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">総評価額</div>
          <div className="text-3xl font-bold text-gray-800">¥{portfolioData.totalValue.toLocaleString()}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">含み損益</div>
          <div className="text-3xl font-bold text-green-600 flex items-center gap-2">
            <TrendingUp size={28} />
            +¥{portfolioData.unrealizedPL.toLocaleString()}
          </div>
          <div className="text-sm text-green-600">+{portfolioData.unrealizedPLPercent}%</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">年間実現損益</div>
          <div className="text-3xl font-bold text-blue-600">+¥{portfolioData.realizedPLYear.toLocaleString()}</div>
        </div>
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="text-sm text-gray-500 mb-2">総合スコア</div>
          <div className="flex items-center justify-center mt-2">
            <OverallScoreBadge score={portfolioData.overallScore} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-lg shadow col-span-2">
          <h3 className="text-lg font-bold mb-4">保有銘柄 TOP5 リスク</h3>
          <div className="space-y-3">
            {portfolioData.holdings.map((stock) => (
              <div key={stock.code} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center gap-3">
                  <button onClick={() => toggleFavorite(stock.code)}>
                    <Star size={18} className={favorites.includes(stock.code) ? 'fill-yellow-400 text-yellow-400' : 'text-gray-400'} />
                  </button>
                  <div>
                    <div className="font-bold">{stock.code} {stock.name}</div>
                    <div className="text-sm text-gray-500">{stock.sector}</div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="font-bold">¥{stock.currentPrice.toLocaleString()}</div>
                    <div className={stock.plPercent > 0 ? 'text-green-600 text-sm' : 'text-red-600 text-sm'}>
                      {stock.plPercent > 0 ? '+' : ''}{stock.plPercent}%
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <ScoreCircle score={stock.fundamental} size="sm" />
                    <ScoreCircle score={stock.supply} size="sm" />
                    <ScoreCircle score={stock.risk} size="sm" />
                  </div>
                  <ScoreCircle score={stock.overall} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">セクター別配分</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={sectorData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label>
                {sectorData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {sectorData.map((sector) => (
              <div key={sector.name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded" style={{ backgroundColor: sector.color }}></div>
                  <span>{sector.name}</span>
                </div>
                <span className="font-bold">{sector.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-bold mb-4">ポートフォリオ分析</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" />
              <PolarRadiusAxis angle={90} domain={[0, 100]} />
              <Radar name="スコア" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.6} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-4">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <AlertTriangle className="text-orange-500" />
              注意アラート
            </h3>
            <div className="space-y-3">
              {alerts.map((alert, idx) => (
                <div key={idx} className={`p-3 rounded border-l-4 ${alert.priority === 'high' ? 'border-red-500 bg-red-50' : 'border-yellow-500 bg-yellow-50'}`}>
                  <div className="text-sm font-medium">{alert.message}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-bold mb-4">最近のニュース</h3>
            <div className="space-y-2">
              {recentNews.map((news, idx) => (
                <div key={idx} className="p-2 hover:bg-gray-50 rounded cursor-pointer">
                  <div className="text-xs text-gray-500">{news.date}</div>
                  <div className="text-sm font-medium">{news.title}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
