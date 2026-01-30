import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { DemoEcommerceWebsite } from './components/DemoEcommerceWebsite'
import { ChatWidget } from './components/ChatWidget'
import { DocumentsPage } from './components/DocumentsPage'

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<DemoEcommerceWebsite />} />
        <Route path="/documents" element={<DocumentsPage />} />
      </Routes>
      <ChatWidget companyId="techstore_123" />
    </>
  )
}

export default App
