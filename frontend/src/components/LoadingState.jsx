export default function LoadingState({ currentStage, error }) {
  const stages = [
    { id: 'transcript', label: 'Fetching transcript from YouTube', icon: '📄' },
    { id: 'style', label: 'Analyzing writing style', icon: '✍️' },
    { id: 'generate', label: 'Generating blog post', icon: '📝' },
  ];

  const getStageClass = (stageId) => {
    const stageOrder = stages.map(s => s.id);
    const currentIndex = stageOrder.indexOf(currentStage);
    const stageIndex = stageOrder.indexOf(stageId);
    
    if (stageIndex < currentIndex) return 'progress-step completed';
    if (stageIndex === currentIndex) return 'progress-step active';
    return 'progress-step';
  };

  const getStageIcon = (stage, stageId) => {
    const stageOrder = stages.map(s => s.id);
    const currentIndex = stageOrder.indexOf(currentStage);
    const stageIndex = stageOrder.indexOf(stageId);
    
    if (stageIndex < currentIndex) return '✓';
    return stage.icon;
  };

  if (error) {
    return (
      <div className="card">
        <div className="loading-container">
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❌</div>
          <h3 className="loading-text" style={{ color: 'var(--error)' }}>Something went wrong</h3>
          <p className="loading-subtext">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="loading-container">
        <div className="loading-spinner" />
        <h3 className="loading-text">Processing your video...</h3>
        <p className="loading-subtext">This may take a few minutes depending on video length</p>
        
        <div className="progress-steps">
          {stages.map((stage) => (
            <div key={stage.id} className={getStageClass(stage.id)}>
              <div className="progress-step-icon">
                {getStageIcon(stage, stage.id)}
              </div>
              <span className="progress-step-label">{stage.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

