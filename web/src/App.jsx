import React, { useState } from 'react';
import LandingPage from './pages/LandingPage';
import AppPage from './pages/AppPage';

function App() {
  const [currentPage, setCurrentPage] = useState('landing');

  const navigateToApp = () => setCurrentPage('app');
  const navigateToLanding = () => setCurrentPage('landing');

  return (
    <>
      {currentPage === 'landing' ? (
        <LandingPage onStart={navigateToApp} />
      ) : (
        <AppPage onBack={navigateToLanding} />
      )}
    </>
  );
}

export default App;
