import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import StockDetail from './pages/StockDetail';
import SmartScreener from './pages/SmartScreener';
import Console from './pages/Console';
import './App.css';

// Initialize Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/stock/:code" element={<StockDetail />} />
          <Route path="/screener" element={<SmartScreener />} />
          <Route path="/console" element={<Console />} />
          {/* Add more routes later */}
        </Routes>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
