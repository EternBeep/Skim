import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// Remove the HTML preloader once React has painted the welcome screen
requestAnimationFrame(() => {
  const el = document.getElementById('preloader')
  if (el) el.remove()
})
