import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  plugins: [
    react({
      include: /src\/.*\.(t|j)sx?$/,
      // enable processing of .js files that contain JSX
      babel: false,
    }),
  ],
})
