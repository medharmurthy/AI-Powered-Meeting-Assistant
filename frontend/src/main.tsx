import React from 'react';
import ReactDOM from 'react-dom/client';
import '@fontsource-variable/literata/index.css';
import '@fontsource-variable/literata/standard-italic.css';
import '@fontsource-variable/hanken-grotesk/index.css';
import './styles/tokens.css';
import './styles/base.css';
import './styles/layout.css';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
