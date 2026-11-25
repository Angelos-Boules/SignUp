import { useState } from 'react'
import { SignUpForm } from './components/SignUpForm'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
        <SignUpForm />
    </>
  )
}

export default App
