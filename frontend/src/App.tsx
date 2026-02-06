import { Routes, Route } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { modules } from '@/modules/module-registry'
import { HomePage } from '@/modules/home/HomePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        {/* Home screen */}
        <Route index element={<HomePage />} />

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
