import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    tailwindcss(),
    react()
  ],
  server: {
    proxy: {
      '/run': 'http://localhost:8000',
      '/upload_resume': 'http://localhost:8000',
      '/manager_debrief': 'http://localhost:8000',
      '/fairness': 'http://localhost:8000',
      '/interviews': 'http://localhost:8000',
      '/schedule_interview': 'http://localhost:8000',
      '/start_meet_session': 'http://localhost:8000',
      '/oral_interview': 'http://localhost:8000',
      '/query_email': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/outbox': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      }
    }
  }
})

