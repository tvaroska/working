import { Routes, Route, Navigate } from 'react-router-dom';
import { AgentConsole } from '@bridge/agent-console';
import { OpsDashboard } from '@bridge/ops-dashboard';
import { ProviderPortal } from '@bridge/provider-portal';
import { Timewarp } from '@bridge/timewarp';
import Layout from './Layout';
import Theater from './Theater';
import Timeline from './Timeline';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/theater" replace />} />
        <Route path="theater" element={<Theater />} />
        <Route path="console" element={<AgentConsole />} />
        <Route path="ops" element={<OpsDashboard />} />
        <Route path="portal" element={<ProviderPortal />} />
        <Route path="timewarp" element={<Timewarp />} />
        <Route path="timeline" element={<Timeline />} />
      </Route>
    </Routes>
  );
}

export default App;
