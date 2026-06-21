import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

/**
 * Composable for Server-Sent Events (SSE) streaming.
 *
 * Currently the backend returns full JSON responses. When backend
 * adds SSE support (text/event-stream), this composable will handle
 * streaming message reception.
 */
export function useSSE() {
  const streamText = ref('')
  const isStreaming = ref(false)
  const error = ref(null)

  function connect(url) {
    const authStore = useAuthStore()
    streamText.value = ''
    isStreaming.value = true
    error.value = null

    // Append token as query param (EventSource doesn't support custom headers)
    const sep = url.includes('?') ? '&' : '?'
    const fullUrl = `${url}${sep}token=${authStore.accessToken}`

    const eventSource = new EventSource(fullUrl)

    eventSource.addEventListener('message', (event) => {
      if (event.data === '[DONE]') {
        isStreaming.value = false
        eventSource.close()
        return
      }
      try {
        const parsed = JSON.parse(event.data)
        streamText.value += parsed.content || ''
      } catch {
        streamText.value += event.data
      }
    })

    eventSource.addEventListener('error', (event) => {
      error.value = 'SSE connection error'
      isStreaming.value = false
      eventSource.close()
    })

    // Return cleanup function
    return () => {
      eventSource.close()
      isStreaming.value = false
    }
  }

  return {
    streamText,
    isStreaming,
    error,
    connect,
  }
}
