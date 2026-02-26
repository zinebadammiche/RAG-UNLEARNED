import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export const ragApi = {
  health: () => api.get('/health'),
  query: (question, n_results = 3) =>
    api.post('/query', { question, n_results }),
  documents: () => api.get('/documents'),
}

export default api
