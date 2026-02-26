import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import { UserPreferencesProvider } from '@/contexts/UserPreferencesContext'
import { AppProvider } from '@/contexts/AppContext'
import { JobProvider } from '@/contexts/JobContext'
import { HistoryProvider } from '@/contexts/HistoryContext'
import ErrorBoundary from '@/components/ErrorBoundary'
import LoadingScreen from '@/components/LoadingScreen'
import { SuperAdminRoute } from '@/components/SuperAdminRoute'

const Home = lazy(() => import('@/pages/Home'))
const Settings = lazy(() => import('@/pages/Settings'))
const UserManagement = lazy(() => import('@/pages/UserManagement'))



function App() {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <BrowserRouter>
          <AuthProvider>
            <UserPreferencesProvider>
              <Toaster position="top-center" offset="16px" />
              <Suspense fallback={<LoadingScreen />}>
                <Routes>
                  <Route
                    path="/"
                    element={
                      <AppProvider>
                        <HistoryProvider>
                          <JobProvider>
                            <Home />
                          </JobProvider>
                        </HistoryProvider>
                      </AppProvider>
                    }
                  />
                  <Route
                    path="/settings"
                    element={<Settings />}
                  />
                  <Route
                    path="/users"
                    element={
                      <SuperAdminRoute>
                        <UserManagement />
                      </SuperAdminRoute>
                    }
                  />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </UserPreferencesProvider>
          </AuthProvider>
        </BrowserRouter>
      </ErrorBoundary>
    </ThemeProvider>
  )
}

export default App
