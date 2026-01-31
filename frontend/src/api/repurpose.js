const API_BASE = '/api';
const AUTH_BASE = '/auth';

// Helper to get auth headers
function getAuthHeaders(token) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ============ Health Check ============

export async function healthCheck() {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error('API is not available');
  return response.json();
}

// ============ Auth ============

export async function getGoogleAuthUrl() {
  const response = await fetch(`${AUTH_BASE}/google`);
  if (!response.ok) throw new Error('Failed to get auth URL');
  return response.json();
}

export async function getMe(token) {
  const response = await fetch(`${AUTH_BASE}/me`, {
    headers: getAuthHeaders(token),
  });
  if (!response.ok) throw new Error('Failed to get user');
  return response.json();
}

export async function logout(token) {
  const response = await fetch(`${AUTH_BASE}/logout`, {
    method: 'POST',
    headers: getAuthHeaders(token),
  });
  return response.json();
}

// ============ Styles ============

export async function getStyles(token) {
  const response = await fetch(`${API_BASE}/styles`, {
    headers: getAuthHeaders(token),
  });
  if (!response.ok) throw new Error('Failed to get styles');
  return response.json();
}

export async function createStyle(token, name, styleGuide) {
  const response = await fetch(`${API_BASE}/styles`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ name, style_guide: styleGuide }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create style');
  }
  return response.json();
}

export async function deleteStyle(token, styleId) {
  const response = await fetch(`${API_BASE}/styles/${styleId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  });
  if (!response.ok) throw new Error('Failed to delete style');
  return response.json();
}

// ============ Blogs ============

export async function getBlogs(token) {
  const response = await fetch(`${API_BASE}/blogs`, {
    headers: getAuthHeaders(token),
  });
  if (!response.ok) throw new Error('Failed to get blogs');
  return response.json();
}

export async function getBlog(token, blogId) {
  const response = await fetch(`${API_BASE}/blogs/${blogId}`, {
    headers: getAuthHeaders(token),
  });
  if (!response.ok) throw new Error('Failed to get blog');
  return response.json();
}

export async function deleteBlog(token, blogId) {
  const response = await fetch(`${API_BASE}/blogs/${blogId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(token),
  });
  if (!response.ok) throw new Error('Failed to delete blog');
  return response.json();
}

// ============ Core Features ============

export async function downloadAudio(token, url) {
  const response = await fetch(`${API_BASE}/download`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Download failed');
  }
  return response.json();
}

export async function transcribeAudio(token, audioPath) {
  const response = await fetch(`${API_BASE}/transcribe`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ audio_path: audioPath }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Transcription failed');
  }
  return response.json();
}

export async function analyzeStyle(token, referenceText) {
  const response = await fetch(`${API_BASE}/analyze-style`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ reference_text: referenceText }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Style analysis failed');
  }
  return response.json();
}

export async function generateBlog(token, { transcript, styleGuide, styleId, youtubeUrl, title, outputFormat, outputOption }) {
  const response = await fetch(`${API_BASE}/generate-blog`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ 
      transcript, 
      style_guide: styleGuide,
      style_id: styleId,
      youtube_url: youtubeUrl,
      title: title,
      output_format: outputFormat,
      output_option: outputOption
    }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Content generation failed');
  }
  return response.json();
}
