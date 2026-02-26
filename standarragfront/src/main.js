import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'
import App from './App.vue'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        dark: true,
        colors: {
          background: '#0d0f14',
          surface: '#161a24',
          primary: '#ff6b35',
          secondary: '#ff9a6c',
          accent: '#ffb347',
          error: '#ff4757',
          success: '#2ed573',
          warning: '#ffa502',
          info: '#1e90ff',
        },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
