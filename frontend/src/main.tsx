import './index.css'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import App from './ui/App'
import ProvidersPage from './ui/ProvidersPage'
import VMsPage from './ui/VMsPage'
import JobsPage from './ui/JobsPage'

const router = createBrowserRouter([
  { path: '/', element: <App />,
    children: [
      { index: true, element: <VMsPage/> },
      { path: 'providers', element: <ProvidersPage/> },
      { path: 'jobs', element: <JobsPage/> },
    ]
  }
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
