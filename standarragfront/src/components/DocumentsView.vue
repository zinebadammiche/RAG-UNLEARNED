<template>
  <div>
    <div v-if="loading" class="d-flex justify-center pa-8">
      <v-progress-circular indeterminate color="primary" />
    </div>
    <div v-else-if="data">
      <!-- Summary -->
      <v-row class="mb-4" dense>
        <v-col cols="4">
          <v-card variant="tonal" color="primary" rounded="lg">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-black">{{ data.total }}</div>
              <div class="text-caption mono text-uppercase">Total docs</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="4">
          <v-card variant="tonal" color="success" rounded="lg">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-black">{{ data.retain?.length ?? 0 }}</div>
              <div class="text-caption mono text-uppercase">Retain</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="4">
          <v-card variant="tonal" color="error" rounded="lg">
            <v-card-text class="text-center">
              <div class="text-h4 font-weight-black">{{ data.forget?.length ?? 0 }}</div>
              <div class="text-caption mono text-uppercase">Forget</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Tables -->
      <v-row>
        <v-col cols="12" md="6">
          <div class="section-label mb-2">
            <v-icon color="success" size="small" class="mr-1">mdi-check-circle</v-icon>
            RETAIN SET
          </div>
          <v-table density="compact" class="doc-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Date</th>
                <th>Ère</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in data.retain" :key="doc.doc_id">
                <td class="mono" style="color: #2ed573; font-size: 11px">{{ doc.doc_id }}</td>
                <td class="mono" style="font-size: 10px; opacity: 0.6">{{ doc.date }}</td>
                <td style="font-size: 10px; opacity: 0.5">{{ doc.era }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>

        <v-col cols="12" md="6">
          <div class="section-label mb-2">
            <v-icon color="error" size="small" class="mr-1">mdi-close-circle</v-icon>
            FORGET SET <span style="opacity:0.5">(inclus dans ce RAG)</span>
          </div>
          <v-table density="compact" class="doc-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Date</th>
                <th>Ère</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="doc in data.forget" :key="doc.doc_id" style="opacity: 0.7">
                <td class="mono" style="color: #ff4757; font-size: 11px">{{ doc.doc_id }}</td>
                <td class="mono" style="font-size: 10px; opacity: 0.6">{{ doc.date }}</td>
                <td style="font-size: 10px; opacity: 0.5">{{ doc.era }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ragApi } from '../api.js'

const loading = ref(true)
const data = ref(null)

onMounted(async () => {
  try {
    const res = await ragApi.documents()
    data.value = res.data
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.section-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  opacity: 0.7;
}
.doc-table { background: transparent !important; }
.mono { font-family: 'JetBrains Mono', 'Courier New', monospace; }
</style>
