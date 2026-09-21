import { useState } from 'react'
import './App.css'

function App() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sources, setSources] = useState([])

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!question.trim()) return
    
    setLoading(true)
    setError('')
    setAnswer('')
    setSources([])
    
    try {
      const response = await fetch('http://127.0.0.1:8000/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          top_k: 5,
          generator: 'mistral',
          model: 'mistral-small-latest',
          fallback_to_translation: true
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Server error')
      }
      
      const data = await response.json()
      setAnswer(data.answer)
      setSources(data.sources || [])
    } catch (err) {
      setError(err.message || 'Failed to get answer')
      console.error('Error:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>🤖 RAG Assistant</h1>
        <p>Ask a question about our services</p>
      </header>

      <form onSubmit={handleSubmit} className="form">
        <textarea
          className="question-input"
          placeholder="For example: What services do you provide?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          disabled={loading}
        />
        
        <button 
          type="submit" 
          className="submit-btn"
          disabled={loading || !question.trim()}
        >
          {loading ? '⏳ Think...' : '🔍 Ask'}
        </button>
      </form>

      {error && (
        <div className="error-box">
          <strong>❌ Error:</strong> {error}
        </div>
      )}

      {answer && (
        <div className="answer-box">
          <h2>💬 Answer:</h2>
          <p className="answer-text">{answer}</p>
          
          {sources.length > 0 && (
            <details className="sources">
              <summary>📚 Sources ({sources.length})</summary>
              <ul>
                {sources.map((src, idx) => (
                  <li key={idx}>
                    {src.url ? (
                      <a href={src.url} target="_blank" rel="noopener noreferrer">
                        {src.title || src.url}
                      </a>
                    ) : (
                      <span>{src.title || 'Source'}</span>
                    )}
                    <small> [{src.language?.toUpperCase()}]</small>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

export default App