import { ProductPanel } from './components/ProductPanel'
import { ShowroomCanvas } from './components/ShowroomCanvas'
import './App.css'

function App() {
  return (
    <div className="showroom">
      <ProductPanel />
      <ShowroomCanvas />
    </div>
  )
}

export default App
