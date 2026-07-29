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
      '/run': 'http://127.0.0.1:8000',
      '/upload_resume': 'http://127.0.0.1:8000',
      '/manager_debrief': 'http://127.0.0.1:8000',
      '/fairness': 'http://127.0.0.1:8000',
      '/interviews': 'http://127.0.0.1:8000',
      '/schedule_interview': 'http://127.0.0.1:8000',
      '/start_meet_session': 'http://127.0.0.1:8000',
      '/oral_interview': 'http://127.0.0.1:8000',
      '/query_email': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/outbox': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      }
    }
  }
})

