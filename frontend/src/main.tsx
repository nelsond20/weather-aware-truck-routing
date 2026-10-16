import { StrictMode,Component } from 'react';
import type { ReactNode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles/tokens.css';import './styles/reset.css';import './styles/globals.css';
class ErrorBoundary extends Component<{children:ReactNode},{failed:boolean}>{
  override state={failed:false};
  static getDerivedStateFromError(){return {failed:true};}
  override render(){return this.state.failed?<main><h1>Unable to display routes</h1><p>Reload the page to recover.</p><button onClick={()=>location.reload()}>Reload</button></main>:this.props.children;}
}
const root=document.getElementById('root');if(!root)throw Error('Root element is required.');
createRoot(root).render(<StrictMode><ErrorBoundary><App/></ErrorBoundary></StrictMode>);
