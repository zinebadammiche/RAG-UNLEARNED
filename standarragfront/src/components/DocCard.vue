<template>
  <v-card
    class="doc-card mb-2"
    :class="statusClass"
    variant="outlined"
    rounded="lg"
  >
    <v-card-text class="pa-3">
      <div class="d-flex align-center justify-space-between mb-1">
        <span class="doc-id mono">{{ doc.doc_id }}</span>
        <v-chip
          :color="statusColor"
          size="x-small"
          variant="tonal"
          class="text-uppercase"
        >
          {{ doc.status }}
        </v-chip>
      </div>
      <div class="doc-date mono mb-1">{{ doc.date }}</div>
      <div class="doc-snippet">{{ doc.snippet }}</div>
      <div class="d-flex align-center justify-space-between mt-2">
        <span class="doc-era mono">{{ doc.era }}</span>
        <v-chip size="x-small" variant="text" class="mono" :color="scoreColor(doc.score)">
          {{ (doc.score * 100).toFixed(1) }}% match
        </v-chip>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
const props = defineProps({
  doc: { type: Object, required: true },
})

const statusColor = props.doc.status === 'RETAIN' ? 'success'
  : props.doc.era === 'minority_position' ? 'warning'
  : 'error'

const statusClass = props.doc.status === 'RETAIN' ? 'doc-retain'
  : props.doc.era === 'minority_position' ? 'doc-minority'
  : 'doc-forget'

const scoreColor = (score) =>
  score >= 0.8 ? 'success' : score >= 0.6 ? 'warning' : 'error'
</script>

<style scoped>
.doc-card { transition: border-color 0.2s; }

.doc-retain { border-color: rgba(46, 213, 115, 0.35) !important; }
.doc-forget { border-color: rgba(255, 71, 87, 0.35) !important; opacity: 0.8; }
.doc-minority { border-color: rgba(255, 165, 2, 0.35) !important; }

.doc-id {
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--v-theme-primary));
}
.doc-date {
  font-size: 10px;
  color: rgba(255,255,255,0.4);
}
.doc-snippet {
  font-size: 11px;
  color: rgba(255,255,255,0.6);
  line-height: 1.5;
}
.doc-era {
  font-size: 10px;
  color: rgba(255,255,255,0.3);
}
.mono { font-family: 'JetBrains Mono', 'Courier New', monospace; }
</style>
