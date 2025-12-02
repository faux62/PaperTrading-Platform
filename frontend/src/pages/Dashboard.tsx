export default function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-white mb-6">📊 Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-gray-400 text-sm">Total Portfolio Value</h3>
          <p className="text-2xl font-bold text-white mt-2">$125,432.50</p>
          <p className="text-emerald-400 text-sm mt-1">+2.45% today</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-gray-400 text-sm">Unrealized P&L</h3>
          <p className="text-2xl font-bold text-emerald-400 mt-2">+$5,432.50</p>
          <p className="text-gray-400 text-sm mt-1">+4.53%</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-gray-400 text-sm">Cash Available</h3>
          <p className="text-2xl font-bold text-white mt-2">$24,567.50</p>
          <p className="text-gray-400 text-sm mt-1">19.6% of portfolio</p>
        </div>
      </div>
      <p className="text-gray-500 mt-8 text-center">
        Dashboard page - Coming soon...
      </p>
    </div>
  )
}
