import { Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { modules } from '@/modules/module-registry'

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        {/* Redirect root to first module */}
        <Route index element={<Navigate to={modules[0]?.path || '/data-room'} replace />} />
        
        {/* Render module routes */}
        {modules.map((module) => (
          <Route
            key={module.id}
            path={`${module.path}/*`}
            element={<module.component />}
          />
        ))}
      </Route>
    </Routes>
  )
}

export default App
