import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Console from './pages/Console';
import Ops from './pages/Ops';
import Portal from './pages/Portal';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/console" replace />} />
        <Route path="console" element={<Console />} />
        <Route path="ops" element={<Ops />} />
        <Route path="portal" element={<Portal />} />
      </Route>
    </Routes>
  );
}

export default App;
