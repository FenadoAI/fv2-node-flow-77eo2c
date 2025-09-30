import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Badge } from '@/components/ui/badge';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  TrendingUp, TrendingDown, DollarSign, Award,
  Activity, LogOut, Calendar, Filter
} from 'lucide-react';

const API = `${process.env.REACT_APP_API_URL || 'http://localhost:8001'}/api`;

export default function DashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState(null);
  const [assets, setAssets] = useState([]);
  const [rewardsHistory, setRewardsHistory] = useState([]);
  const [performance, setPerformance] = useState([]);

  // Filter states
  const [dateRange, setDateRange] = useState([30]);
  const [selectedAssets, setSelectedAssets] = useState([]);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/');
      return;
    }
    fetchDashboardData();
  }, [dateRange]);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [overviewRes, assetsRes, rewardsRes, perfRes] = await Promise.all([
        axios.get(`${API}/staking/overview`, { headers }),
        axios.get(`${API}/staking/assets`, { headers }),
        axios.get(`${API}/staking/rewards-history?days=${dateRange[0]}`, { headers }),
        axios.get(`${API}/staking/performance?days=${dateRange[0]}`, { headers })
      ]);

      setOverview(overviewRes.data.data);
      setAssets(assetsRes.data.data);
      setRewardsHistory(rewardsRes.data.data);
      setPerformance(perfRes.data.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        navigate('/');
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/');
  };

  const filteredAssets = selectedAssets.length > 0
    ? assets.filter(asset => selectedAssets.includes(asset.asset_symbol))
    : assets;

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold">
              L
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">Luganodes</h1>
              <p className="text-xs text-slate-400">Staking Dashboard</p>
            </div>
          </div>
          <Button
            onClick={handleLogout}
            variant="outline"
            className="border-slate-700 text-slate-300 hover:bg-slate-800"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-slate-900/90 border-slate-700">
            <CardHeader className="pb-2">
              <CardDescription className="text-slate-400">Total Staked Value</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-white">
                    ${overview?.total_staked_value?.toLocaleString()}
                  </div>
                  <div className={`flex items-center mt-2 text-sm ${overview?.performance_change_24h >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {overview?.performance_change_24h >= 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
                    {Math.abs(overview?.performance_change_24h || 0).toFixed(2)}% (24h)
                  </div>
                </div>
                <DollarSign className="w-12 h-12 text-purple-400 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/90 border-slate-700">
            <CardHeader className="pb-2">
              <CardDescription className="text-slate-400">Total Rewards Earned</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-green-400">
                    ${overview?.total_rewards_earned?.toLocaleString()}
                  </div>
                  <div className="text-sm text-slate-400 mt-2">All time</div>
                </div>
                <Award className="w-12 h-12 text-green-400 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/90 border-slate-700">
            <CardHeader className="pb-2">
              <CardDescription className="text-slate-400">Average APY</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-blue-400">
                    {overview?.average_apy?.toFixed(2)}%
                  </div>
                  <div className="text-sm text-slate-400 mt-2">Across all assets</div>
                </div>
                <Activity className="w-12 h-12 text-blue-400 opacity-50" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/90 border-slate-700">
            <CardHeader className="pb-2">
              <CardDescription className="text-slate-400">Total Assets</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-3xl font-bold text-purple-400">
                    {overview?.total_assets}
                  </div>
                  <div className="text-sm text-slate-400 mt-2">Active stakes</div>
                </div>
                <Filter className="w-12 h-12 text-purple-400 opacity-50" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Date Range Filter */}
        <Card className="bg-slate-900/90 border-slate-700 mb-8">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-white flex items-center">
                  <Calendar className="w-5 h-5 mr-2 text-purple-400" />
                  Date Range Filter
                </CardTitle>
                <CardDescription className="text-slate-400 mt-1">
                  Showing data for the last {dateRange[0]} days
                </CardDescription>
              </div>
              <Badge variant="outline" className="bg-purple-500/20 text-purple-300 border-purple-500/50">
                {dateRange[0]} Days
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Slider
                value={dateRange}
                onValueChange={setDateRange}
                min={7}
                max={90}
                step={1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-slate-500">
                <span>7 days</span>
                <span>30 days</span>
                <span>60 days</span>
                <span>90 days</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Performance Chart */}
          <Card className="bg-slate-900/90 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Portfolio Performance</CardTitle>
              <CardDescription className="text-slate-400">
                Total value over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={performance}>
                  <defs>
                    <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px'
                    }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#8b5cf6"
                    fillOpacity={1}
                    fill="url(#colorValue)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Rewards History Chart */}
          <Card className="bg-slate-900/90 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Rewards History</CardTitle>
              <CardDescription className="text-slate-400">
                Daily rewards earned
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={rewardsHistory}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                  />
                  <YAxis
                    stroke="#94a3b8"
                    tick={{ fill: '#94a3b8' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px'
                    }}
                    labelStyle={{ color: '#e2e8f0' }}
                  />
                  <Bar dataKey="amount" fill="#10b981" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* Assets List */}
        <Card className="bg-slate-900/90 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white">Staked Assets</CardTitle>
            <CardDescription className="text-slate-400">
              Your active staking positions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {filteredAssets.map((asset) => (
                <div
                  key={asset.id}
                  className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700 hover:border-purple-500/50 transition-colors"
                >
                  <div className="flex items-center space-x-4">
                    <img
                      src={asset.logo_url}
                      alt={asset.asset_name}
                      className="w-12 h-12 rounded-full"
                    />
                    <div>
                      <div className="font-semibold text-white">{asset.asset_name}</div>
                      <div className="text-sm text-slate-400">{asset.asset_symbol}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-8 text-right">
                    <div>
                      <div className="text-xs text-slate-400">Amount Staked</div>
                      <div className="font-semibold text-white">{asset.amount_staked.toFixed(2)} {asset.asset_symbol}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Current Value</div>
                      <div className="font-semibold text-white">${asset.current_value.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">APY</div>
                      <div className="font-semibold text-blue-400">{asset.apy.toFixed(2)}%</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Rewards Earned</div>
                      <div className="font-semibold text-green-400">${asset.rewards_earned.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
