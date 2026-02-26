<template>
  <div class="chat-app">

    <!-- Header -->
    <header class="chat-header">
      <div class="header-left">
        <div class="header-icon">AI</div>
        <div>
          <div class="header-title">Standard RAG</div>
          
        </div>
      </div>
      <div class="header-status">
        <span class="status-dot" :class="{ online: health.ok }"></span>
        <span class="status-text">
          {{ health.ok ? `${health.docs} docs` : 'offline' }}
        </span>
      </div>
    </header>

    <!-- Messages -->
    <main class="chat-messages" ref="messagesEl">

      <!-- Welcome -->
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon"></div>
        <div class="welcome-title">Standard RAG</div>
        <div class="welcome-desc">
          Ce RAG utilise tous les documents historiques  
        </div>
        <div class="preset-grid">
          <button
            v-for="p in presets"
            :key="p"
            class="preset-btn"
            @click="sendPreset(p)"
          >{{ p }}</button>
        </div>
      </div>

      <!-- Message list -->
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message-row"
        :class="msg.role"
      >

        <!-- User -->
        <div v-if="msg.role === 'user'" class="bubble user-bubble">
          {{ msg.content }}
        </div>

        <!-- Assistant -->
        <div v-if="msg.role === 'assistant'" class="assistant-wrap">
          <div class="assistant-avatar">AI</div>
          <div class="bubble assistant-bubble">

            <!-- Loading -->
            <div v-if="msg.loading" class="typing">
              <span></span><span></span><span></span>
            </div>

            <!-- Answer -->
            <div
              v-else
              class="answer-text"
              v-html="renderMarkdown(msg.content)"
            ></div>

            <!-- Retrieved docs -->
            <div v-if="msg.docs && msg.docs.length" class="docs-section">
              <button class="docs-toggle" @click="msg.showDocs = !msg.showDocs">
                <span>{{ msg.docs.length }} documents récupérés</span>
                <span>{{ msg.showDocs ? '▲' : '▼' }}</span>
              </button>

              <div v-if="msg.showDocs" class="docs-list">
                <div
                  v-for="doc in msg.docs"
                  :key="doc.doc_id"
                  class="doc-item"
                  :class="doc.status === 'RETAIN' ? 'doc-retain' : 'doc-forget'"
                >
                  <div class="doc-header">
                    <span class="doc-id">{{ doc.doc_id }}</span>
                    <span
                      class="doc-badge"
                      :class="doc.status === 'RETAIN' ? 'badge-retain' : 'badge-forget'"
                    >
                      {{ doc.status }}
                    </span>
                    <span class="doc-score">
                      {{ (doc.score * 100).toFixed(0) }}%
                    </span>
                  </div>
                  <div class="doc-snippet">{{ doc.snippet }}</div>
                </div>
              </div>
            </div>

          </div>
        </div>

      </div>

      <div ref="bottomEl"></div>
    </main>

    <!-- Input -->
    <footer class="chat-footer">
      <div class="input-wrap">
        <textarea
          v-model="input"
          class="chat-input"
          placeholder="Posez une question  ..."
          rows="1"
          @keydown.enter.exact.prevent="send"
          @input="autoResize"
          ref="inputEl"
        ></textarea>

        <button
          class="send-btn"
          :disabled="!input.trim() || loading"
          @click="send"
        >
          <span v-if="loading">...</span>
          <span v-else>Envoyer</span>
        </button>
      </div>

      <div class="footer-hint">
        Entrée pour envoyer · Shift+Entrée pour nouvelle ligne
      </div>
    </footer>

  </div>
</template>
<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ragApi } from './api.js'

const messages = ref([])
const input = ref('')
const loading = ref(false)
const health = ref({ ok: false, docs: 0 })
const messagesEl = ref(null)
const bottomEl = ref(null)
const inputEl = ref(null)

const presets = [
  'Quelles sont les options pour résoudre le conflit du Sahara Occidental ?',
  'Quelles résolutions ont renouvelé le mandat de la MINURSO ?',
  'Quelle est la position du Polisario Front ?',
  'Qu\'est-ce que la résolution 2797 de 2025 ?',
]

onMounted(async () => {
  try {
    const res = await ragApi.health()
    health.value = { ok: true, docs: res.data.collection_size }
  } catch {
    health.value.ok = false
  }
})

function renderMarkdown(text) {
  if (!text) return ''
  return text
    // Bold **text**
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic *text*
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Code `text`
    .replace(/`(.*?)`/g, '<code>$1</code>')
    // Headers ### ## #
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h2>$1</h2>')
    .replace(/^# (.*$)/gm, '<h1>$1</h1>')
    // Numbered list
    .replace(/^\d+\.\s+(.*$)/gm, '<li>$1</li>')
    // Bullet list
    .replace(/^[-*]\s+(.*$)/gm, '<li>$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
    // Line breaks
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    // Wrap in paragraph
    .replace(/^(?!<[hup])(.+)/, '<p>$1')
}

function scrollToBottom() {
  nextTick(() => {
    bottomEl.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 150) + 'px'
}

async function sendPreset(text) {
  input.value = text
  await send()
}

async function send() {
  if (!input.value.trim() || loading.value) return

  const question = input.value.trim()
  input.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'

  // Add user message
  messages.value.push({ role: 'user', content: question })
  scrollToBottom()

  // Add loading assistant message
  const assistantMsg = {
    role: 'assistant',
    content: '',
    loading: true,
    docs: [],
    showDocs: false,
  }
  messages.value.push(assistantMsg)
  loading.value = true
  scrollToBottom()

  try {
    const res = await ragApi.query(question, 3)
    assistantMsg.content = res.data.answer
    assistantMsg.docs = res.data.retrieved_documents
    assistantMsg.loading = false
  } catch (e) {
    assistantMsg.content = ' Erreur lors de la requête. Vérifiez que le backend tourne sur le port 8000.'
    assistantMsg.loading = false
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'DM Sans', sans-serif;
  background: #f0f4f8;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

#app {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-app {
  width: 100%;
  max-width: 780px;
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  box-shadow: 0 0 40px rgba(0,0,0,0.08);
}

/* ── Header ─────────────────────────────────── */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e8edf2;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  width: 40px; height: 40px;
  background: #ebf3ff;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a2332;
}

.header-sub {
  font-size: 12px;
  color: #8896a8;
  margin-top: 1px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f5f8fb;
  padding: 6px 12px;
  border-radius: 20px;
}

.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #cbd5e1;
}
.status-dot.online { background: #22c55e; }

.status-text {
  font-size: 12px;
  font-family: 'DM Mono', monospace;
  color: #5a6a7a;
}

/* ── Messages ────────────────────────────────── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 24px 8px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  scroll-behavior: smooth;
}

.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }
.chat-messages::-webkit-scrollbar-thumb { background: #d1dae6; border-radius: 4px; }

/* Welcome */
.welcome {
  text-align: center;
  padding: 40px 20px;
  margin: auto;
  max-width: 480px;
}
.welcome-icon { font-size: 48px; margin-bottom: 16px; }
.welcome-title {
  font-size: 22px; font-weight: 600;
  color: #1a2332; margin-bottom: 8px;
}
.welcome-desc {
  font-size: 14px; color: #6b7f94;
  line-height: 1.6; margin-bottom: 24px;
}
.preset-grid {
  display: flex; flex-direction: column; gap: 8px;
}
.preset-btn {
  background: #f5f8fb;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 16px;
  font-size: 13px;
  font-family: 'DM Sans', sans-serif;
  color: #2d5fa6;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}
.preset-btn:hover {
  background: #ebf3ff;
  border-color: #2d5fa6;
}

/* Message rows */
.message-row {
  display: flex;
}
.message-row.user { justify-content: flex-end; }
.message-row.assistant { justify-content: flex-start; }

/* Bubbles */
.bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.6;
}

.user-bubble {
  background: #2d5fa6;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.assistant-wrap {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  max-width: 85%;
}

.assistant-avatar {
  width: 32px; height: 32px;
  background: #ebf3ff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600;
  color: #2d5fa6;
  flex-shrink: 0;
}

.assistant-bubble {
  background: #f5f8fb;
  border: 1px solid #e8edf2;
  color: #1a2332;
  border-bottom-left-radius: 4px;
  max-width: 100%;
}

/* Typing indicator */
.typing {
  display: flex;
  gap: 4px;
  padding: 4px 0;
  align-items: center;
}
.typing span {
  width: 7px; height: 7px;
  background: #8896a8;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* Answer text — markdown rendered as plain styled text */
.answer-text {
  color: #1a2332;
  font-size: 14px;
  line-height: 1.7;
}
.answer-text p { margin-bottom: 10px; }
.answer-text p:last-child { margin-bottom: 0; }
.answer-text h1, .answer-text h2, .answer-text h3 {
  font-weight: 600;
  color: #1a2332;
  margin: 12px 0 6px;
}
.answer-text h1 { font-size: 17px; }
.answer-text h2 { font-size: 15px; }
.answer-text h3 { font-size: 14px; }
.answer-text strong { font-weight: 600; color: #1a2332; }
.answer-text em { font-style: italic; color: #4a5568; }
.answer-text code {
  font-family: 'DM Mono', monospace;
  background: #e8edf2;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
  color: #2d5fa6;
}
.answer-text ul {
  padding-left: 20px;
  margin: 8px 0;
}
.answer-text li {
  margin-bottom: 4px;
  color: #1a2332;
}

/* Retrieved docs */
.docs-section {
  margin-top: 14px;
  border-top: 1px solid #e8edf2;
  padding-top: 10px;
}
.docs-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  font-family: 'DM Sans', sans-serif;
  color: #6b7f94;
  padding: 2px 0;
}
.docs-toggle:hover { color: #2d5fa6; }
.docs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}
.doc-item {
  border-radius: 8px;
  padding: 10px 12px;
  border-left: 3px solid transparent;
}
.doc-retain {
  background: #f0fdf4;
  border-left-color: #22c55e;
}
.doc-forget {
  background: #fff5f5;
  border-left-color: #f87171;
}
.doc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.doc-id {
  font-family: 'DM Mono', monospace;
  font-size: 11px;
  font-weight: 500;
  color: #2d5fa6;
}
.doc-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.badge-retain { background: #dcfce7; color: #16a34a; }
.badge-forget { background: #fee2e2; color: #dc2626; }
.doc-score {
  font-size: 10px;
  font-family: 'DM Mono', monospace;
  color: #8896a8;
  margin-left: auto;
}
.doc-snippet {
  font-size: 11px;
  color: #6b7f94;
  line-height: 1.5;
}

/* ── Footer ──────────────────────────────────── */
.chat-footer {
  padding: 16px 24px 20px;
  border-top: 1px solid #e8edf2;
  background: #fff;
}
.input-wrap {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: #f5f8fb;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  padding: 10px 12px;
  transition: border-color 0.2s;
}
.input-wrap:focus-within {
  border-color: #2d5fa6;
  background: #fff;
}
.chat-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  resize: none;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  color: #1a2332;
  line-height: 1.5;
  max-height: 150px;
  overflow-y: auto;
}
.chat-input::placeholder { color: #a0aec0; }

.send-btn {
  width: 100px; height: 36px;
  border-radius: 10px;
  border: none;
  background: #2d5fa6;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s;
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) { background: #1e4a8a; }
.send-btn:disabled { background: #cbd5e1; cursor: not-allowed; }

.footer-hint {
  margin-top: 8px;
  font-size: 11px;
  color: #a0aec0;
  text-align: center;
}
</style>