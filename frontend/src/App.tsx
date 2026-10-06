import React from 'react';
import { Route, Switch } from 'wouter';
import { Home } from './pages/Home';
import { RunView } from './pages/RunView';

export const App: React.FC = () => {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/r/:id" component={RunView} />
      <Route component={Home} />
    </Switch>
  );
};

export default App;
