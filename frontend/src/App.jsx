import { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import StepIndicator from './components/StepIndicator';
import UrlInput from './components/UrlInput';
import LoadingState from './components/LoadingState';
import BlogOutput from './components/BlogOutput';
import AuthButton from './components/AuthButton';
import UserMenu from './components/UserMenu';
import BlogHistory from './components/BlogHistory';
import { getTranscript, generateBlog } from './api/repurpose';

function AppContent() {
  const { user, token, loading: authLoading, defaultStyleId, refetchUserData } = useAuth();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState('');
  const [error, setError] = useState('');
  const [blogContent, setBlogContent] = useState('');
  const [styleText, setStyleText] = useState('');
  const [styleMode, setStyleMode] = useState('none');
  const [selectedStyleId, setSelectedStyleId] = useState(null);
  const [outputFormat, setOutputFormat] = useState({ format: 'blog', option: null });
  const [showHistory, setShowHistory] = useState(false);
  const [currentUrl, setCurrentUrl] = useState('');
  const [currentTitle, setCurrentTitle] = useState('');

  const handleGenerate = async (url, style, styleId, format, mode) => {
    if (!user || !token) {
      setError('Please log in to generate content');
      return;
    }

    setLoading(true);
    setError('');
    setStep(2);
    setCurrentUrl(url);

    const payload = {
      transcript: null,
      styleGuide: '',
      styleId: null,
      youtubeUrl: url,
      title: null,
      outputFormat: format.format,
      outputOption: format.option,
    };

    if (mode === 'saved') {
      payload.styleId = styleId;
    } else if (mode === 'custom' && styleId) {
      payload.styleId = styleId;
    }
    
    try {
      setCurrentStage('transcript');
      const transcriptResult = await getTranscript(token, url);
      setCurrentTitle(transcriptResult.title);
      payload.transcript = transcriptResult.text;
      payload.title = transcriptResult.title;

      setCurrentStage('generate');
      const blogResult = await generateBlog(token, payload);

      setBlogContent(blogResult.blog_content);
      await refetchUserData();
      setStep(3);
      setLoading(false);

    } catch (err) {
      console.error('Error:', err);
      setError(err.message || 'An unexpected error occurred');
      setLoading(false);
    }
  };

  const handleReset = () => {
    setStep(1);
    setLoading(false);
    setCurrentStage('');
    setError('');
    setBlogContent('');
    setStyleText('');
    setStyleMode(defaultStyleId ? 'saved' : 'none');
    setSelectedStyleId(defaultStyleId || null);
    setOutputFormat({ format: 'blog', option: null });
    setCurrentUrl('');
    setCurrentTitle('');
  };

  // Get output type label for display
  const getOutputLabel = () => {
    switch (outputFormat?.format) {
      case 'linkedin': return 'LinkedIn Post';
      case 'twitter': return outputFormat?.option === 'thread' ? 'Twitter Thread' : 'Tweet';
      default: return 'Blog';
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <div className="logo-icon">⚡</div>
          <div>
            <h1>repurpose.ai</h1>
            <span>Video to Content in seconds</span>
          </div>
        </div>
        
        <div className="header-actions">
          {authLoading ? null : user ? (
            <UserMenu onShowHistory={() => setShowHistory(true)} />
          ) : (
            <AuthButton />
          )}
        </div>
      </header>

      <main className="main-content">
        <StepIndicator currentStep={step} />

        {step === 1 && !loading && (
          <UrlInput
            onSubmit={handleGenerate}
            styleText={styleText}
            onStyleChange={setStyleText}
            styleMode={styleMode}
            onStyleModeChange={setStyleMode}
            selectedStyleId={selectedStyleId}
            onStyleIdChange={setSelectedStyleId}
            outputFormat={outputFormat}
            onOutputFormatChange={setOutputFormat}
          />
        )}

        {step === 2 && loading && (
          <LoadingState currentStage={currentStage} error={error} />
        )}

        {step === 2 && !loading && error && (
          <div className="card">
            <div className="loading-container">
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❌</div>
              <h3 className="loading-text" style={{ color: 'var(--error)' }}>Something went wrong</h3>
              <p className="loading-subtext">{error}</p>
              <div className="new-generation">
                <button className="btn btn-primary" onClick={handleReset}>
                  <span>↺</span>
                  <span>Try Again</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 3 && blogContent && (
          <BlogOutput 
            content={blogContent} 
            onReset={handleReset} 
            outputType={getOutputLabel()}
          />
        )}
      </main>

      {showHistory && (
        <BlogHistory onClose={() => setShowHistory(false)} />
      )}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
