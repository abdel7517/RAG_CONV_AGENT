import React from 'react'

export function ChatMessage({ role, content }) {
  return (
    <div className={`message ${role}`}>
      <span className="message-label">
        {role === 'user' ? 'Vous' : 'Agent'}
      </span>
      <div className="message-content">
        {content}
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div className="message assistant">
      <span className="message-label">Agent</span>
      <div className="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  )
}
