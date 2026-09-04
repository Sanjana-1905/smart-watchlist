import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import StockDetail from './pages/StockDetail';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/stock/:symbol" element={<StockDetail />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
