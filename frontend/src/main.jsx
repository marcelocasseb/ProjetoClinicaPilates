import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import AvisoVersao from './components/AvisoVersao.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
    <AvisoVersao />
  </StrictMode>,
)
