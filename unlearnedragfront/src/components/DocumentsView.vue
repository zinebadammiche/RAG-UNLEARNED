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
              <div class="text-h4 font-weight-black">{{ data.total_in_collection }}</div>
              <div class="text-caption mono text-uppercase">Dans le RAG</div>
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
              <div class="text-h4 font-weight-black">{{ data.forgotten?.length ?? 0 }}</div>
              <div class="text-caption mono text-uppercase">Oubliés</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Active docs -->
      <div class="section-label mb-2">
        <v-icon color="success" size="small" class="mr-1">mdi-check-circle</v-icon>
        RETAIN SET — Actifs dans ce RAG
      </div>
      <v-table density="compact" class="doc-table mb-6">
        <thead>
          <tr>
            <th>Document</th>
            <th>Date</th>
            <th>Type</th>
            <th>Ère</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in data.retain" :key="doc.doc_id">
            <td class="mono" style="color: #00d4aa; font-size: 11px">{{ doc.doc_id }}</td>
            <td class="mono" style="font-size: 10px; opacity: 0.6">{{ doc.date }}</td>
            <td style="font-size: 10px; opacity: 0.7">{{ doc.type }}</td>
            <td style="font-size: 10px; opacity: 0.5">{{ doc.era }}</td>
          </tr>
        </tbody>
      </v-table>

      <!-- Forgotten docs -->
      <div class="section-label mb-2">
        <v-icon color="error" size="small" class="mr-1">mdi-delete</v-icon>
        FORGET SET — Exclus par Machine Unlearning
      </div>
      <v-table density="compact" class="doc-table">
        <thead>
          <tr>
            <th>Document</th>
            <th>Raison</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in data.forgotten" :key="doc.doc_id" style="opacity: 0.55">
            <td class="mono" style="color: #ff4757; font-size: 11px; text-decoration: line-through">
              {{ doc.doc_id }}
            </td>
            <td style="font-size: 10px; opacity: 0.8">{{ doc.reason }}</td>
          </tr>
        </tbody>
      </v-table>
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
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 1px; opacity: 0.7;
}
.doc-table { background: transparent !important; }
.mono { font-family: 'JetBrains Mono', 'Courier New', monospace; }
</style>
