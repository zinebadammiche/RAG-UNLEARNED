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
          background: '#080f0e',
          surface: '#0f1f1d',
          primary: '#00d4aa',
          secondary: '#00b894',
          accent: '#55efc4',
          error: '#ff4757',
          success: '#00d4aa',
          warning: '#ffa502',
          info: '#0984e3',
        },
      },
    },
  },
})

createApp(App).use(vuetify).mount('#app')
