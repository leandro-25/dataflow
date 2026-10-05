import { Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { HomePage } from './pages/HomePage';
import { SourcesPage } from './pages/SourcesPage';
import { IngestionsPage } from './pages/IngestionsPage';
import { StagingPage } from './pages/StagingPage';
import { DimensionsPage } from './pages/DimensionsPage';
import { FactsPage } from './pages/FactsPage';
import { MetricsPage } from './pages/MetricsPage';
import { DashboardsPage } from './pages/DashboardsPage';
import { PipelinePage } from './pages/PipelinePage';
import { CatalogPage } from './pages/CatalogPage';
import { SettingsPage } from './pages/SettingsPage';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/sources" element={<SourcesPage />} />
        <Route path="/ingestions" element={<IngestionsPage />} />
        <Route path="/staging" element={<StagingPage />} />
        <Route path="/dimensions" element={<DimensionsPage />} />
        <Route path="/facts" element={<FactsPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
        <Route path="/dashboards" element={<DashboardsPage />} />
        <Route path="/pipeline" element={<PipelinePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
