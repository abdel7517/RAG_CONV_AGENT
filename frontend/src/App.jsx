import React from 'react'
import { DemoEcommerceWebsite } from './components/DemoEcommerceWebsite'
import { ChatWidget } from './components/ChatWidget'

function App() {
  return (
    <>
      <DemoEcommerceWebsite />
      <ChatWidget companyId="techstore_123" />
    </>
  )
}

export default App
