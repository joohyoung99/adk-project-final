import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

type ChatMessage = {
  id: number
  sender: 'user' | 'bot'
  text: string
  createdAt: string
}

type ChatSession = {
  localId: string
  sessionId: string | null
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}

type QueryResponse = {
  success: boolean
  data?: {
    answer?: string
    session_id?: string
  }
  error?: string
}

type LogEntry = {
  id: number
  sessionLocalId: string
  level: 'info' | 'error'
  message: string
  createdAt: string
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const CHAT_STORAGE_KEY = 'didim-rag-chat-state-v1'

const formatTime = () =>
  new Date().toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
  })

const buildSessionTitle = (text: string) => {
  const trimmed = text.trim()
  return trimmed.length > 24 ? `${trimmed.slice(0, 24)}...` : trimmed
}

const createSession = (index: number): ChatSession => {
  const now = formatTime()
  return {
    localId: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    sessionId: null,
    title: `새 대화 ${index}`,
    messages: [
      {
        id: 1,
        sender: 'bot',
        text: '디딤 사내 RAG 챗봇입니다. 사내 문서와 기술 질의를 도와드릴게요.',
        createdAt: now,
      },
    ],
    createdAt: now,
    updatedAt: now,
  }
}

type PersistedChatState = {
  sessions: ChatSession[]
  logs: LogEntry[]
  activeSessionLocalId: string
}

const loadPersistedState = (): PersistedChatState => {
  const fallbackSession = createSession(1)
  const fallback: PersistedChatState = {
    sessions: [fallbackSession],
    logs: [],
    activeSessionLocalId: fallbackSession.localId,
  }

  if (typeof window === 'undefined') {
    return fallback
  }

  try {
    const raw = window.localStorage.getItem(CHAT_STORAGE_KEY)
    if (!raw) {
      return fallback
    }
    const parsed = JSON.parse(raw) as Partial<PersistedChatState>
    const sessions = Array.isArray(parsed.sessions) ? parsed.sessions : fallback.sessions
    const logs = Array.isArray(parsed.logs) ? parsed.logs : []
    const activeSessionLocalId =
      typeof parsed.activeSessionLocalId === 'string' ? parsed.activeSessionLocalId : ''
    const resolvedActiveSessionId =
      sessions.find((session) => session.localId === activeSessionLocalId)?.localId ??
      sessions[0]?.localId ??
      fallback.activeSessionLocalId

    return {
      sessions: sessions.length > 0 ? sessions : fallback.sessions,
      logs,
      activeSessionLocalId: resolvedActiveSessionId,
    }
  } catch {
    return fallback
  }
}

function App() {
  const [initialState] = useState(loadPersistedState)
  const [sessions, setSessions] = useState<ChatSession[]>(initialState.sessions)
  const [activeSessionLocalId, setActiveSessionLocalId] = useState(initialState.activeSessionLocalId)
  const [input, setInput] = useState('')
  const [loadingSessionLocalId, setLoadingSessionLocalId] = useState<string | null>(null)
  const nextMessageIdRef = useRef(2)
  const nextLogIdRef = useRef(1)
  const [logs, setLogs] = useState<LogEntry[]>(initialState.logs)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    document.title = '디딤 사내 RAG 챗봇'
  }, [])

  useEffect(() => {
    if (!sessions.some((session) => session.localId === activeSessionLocalId)) {
      setActiveSessionLocalId(sessions[0]?.localId ?? '')
    }
  }, [sessions, activeSessionLocalId])

  useEffect(() => {
    if (typeof window === 'undefined') {
      return
    }
    const payload: PersistedChatState = {
      sessions,
      logs,
      activeSessionLocalId: activeSessionLocalId || sessions[0]?.localId || '',
    }
    window.localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(payload))
  }, [sessions, logs, activeSessionLocalId])

  const activeSession = useMemo(
    () => sessions.find((session) => session.localId === activeSessionLocalId) ?? sessions[0],
    [sessions, activeSessionLocalId],
  )

  const activeMessages = activeSession?.messages ?? []
  const activeLogs = useMemo(
    () => logs.filter((log) => log.sessionLocalId === activeSession?.localId),
    [logs, activeSession?.localId],
  )
  const activeUserMessages = activeMessages.filter((message) => message.sender === 'user')
  const activeBotMessages = activeMessages.filter((message) => message.sender === 'bot')
  const activeErrorCount = activeLogs.filter((log) => log.level === 'error').length
  const isLoading = loadingSessionLocalId === activeSession?.localId

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeMessages, isLoading, activeSessionLocalId])

  const addLog = (sessionLocalId: string, level: LogEntry['level'], message: string) => {
    const entry: LogEntry = {
      id: nextLogIdRef.current++,
      sessionLocalId,
      level,
      message,
      createdAt: formatTime(),
    }
    setLogs((prev) => [...prev.slice(-149), entry])
  }

  const updateSession = (
    sessionLocalId: string,
    updater: (session: ChatSession) => ChatSession,
  ) => {
    setSessions((prev) =>
      prev.map((session) =>
        session.localId === sessionLocalId ? updater(session) : session,
      ),
    )
  }

  const appendMessage = (sessionLocalId: string, message: ChatMessage) => {
    updateSession(sessionLocalId, (session) => ({
      ...session,
      messages: [...session.messages, message],
      updatedAt: message.createdAt,
    }))
  }

  const startNewSession = () => {
    const nextSession = {
      ...createSession(sessions.length + 1),
      sessionId: null,
    }
    setSessions((prev) => [nextSession, ...prev])
    setActiveSessionLocalId(nextSession.localId)
    setLoadingSessionLocalId(null)
    setInput('')
  }

  const clearAllHistory = () => {
    const resetSession = createSession(1)
    setSessions([resetSession])
    setLogs([])
    setActiveSessionLocalId(resetSession.localId)
    setLoadingSessionLocalId(null)
    setInput('')
    nextMessageIdRef.current = 2
    nextLogIdRef.current = 1
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(CHAT_STORAGE_KEY)
    }
  }

  const sendMessage = async () => {
    const trimmed = input.trim()
    if (!trimmed || !activeSession || loadingSessionLocalId) {
      return
    }

    const targetSessionLocalId = activeSession.localId
    const askedAt = formatTime()
    const userMessage: ChatMessage = {
      id: nextMessageIdRef.current++,
      sender: 'user',
      text: trimmed,
      createdAt: askedAt,
    }

    appendMessage(targetSessionLocalId, userMessage)
    addLog(targetSessionLocalId, 'info', `질문 전송: ${trimmed}`)
    updateSession(targetSessionLocalId, (session) => ({
      ...session,
      title:
        session.messages.filter((message) => message.sender === 'user').length === 0
          ? buildSessionTitle(trimmed)
          : session.title,
      updatedAt: askedAt,
    }))

    setInput('')
    setLoadingSessionLocalId(targetSessionLocalId)

    try {
      const response = await fetch(`${API_BASE_URL}/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: trimmed,
          session_id: activeSession.sessionId,
        }),
      })

      if (!response.ok) {
        throw new Error(`API 요청 실패 (${response.status})`)
      }

      const payload = (await response.json()) as QueryResponse
      if (!payload.success) {
        addLog(
          targetSessionLocalId,
          'error',
          payload.error ?? 'API가 실패 응답을 반환했습니다.',
        )
      }

      if (payload.data?.session_id) {
        updateSession(targetSessionLocalId, (session) => ({
          ...session,
          sessionId: payload.data?.session_id ?? session.sessionId,
        }))
        addLog(targetSessionLocalId, 'info', `세션 갱신: ${payload.data.session_id}`)
      }

      const answer =
        payload.data?.answer ??
        payload.error ??
        '응답을 생성하지 못했습니다. 잠시 후 다시 시도해주세요.'
      appendMessage(targetSessionLocalId, {
        id: nextMessageIdRef.current++,
        sender: 'bot',
        text: answer,
        createdAt: formatTime(),
      })
      addLog(targetSessionLocalId, 'info', '응답 수신 완료')
    } catch (error) {
      const errorText =
        error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'
      addLog(targetSessionLocalId, 'error', errorText)
      appendMessage(targetSessionLocalId, {
        id: nextMessageIdRef.current++,
        sender: 'bot',
        text: `오류가 발생했습니다: ${errorText}`,
        createdAt: formatTime(),
      })
    } finally {
      setLoadingSessionLocalId(null)
    }
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      void sendMessage()
    }
  }

  return (
    <div className="min-h-full bg-gradient-to-b from-rose-100 via-pink-50 to-white px-4 py-6">
      <div className="mx-auto grid h-[90vh] w-full max-w-7xl grid-cols-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)_300px]">
        <aside className="hidden overflow-hidden rounded-2xl border border-pink-200/80 bg-white/90 shadow-xl backdrop-blur lg:flex lg:flex-col">
          <div className="flex items-center justify-between border-b border-pink-100 bg-pink-100/60 px-4 py-3">
            <h2 className="text-sm font-semibold text-rose-700">대화 히스토리</h2>
            <button
              type="button"
              onClick={startNewSession}
              className="rounded-xl bg-rose-500 px-3 py-1.5 text-xs font-medium text-white shadow hover:bg-rose-600"
            >
              + 새 대화
            </button>
          </div>
          <div className="flex-1 space-y-2 overflow-y-auto bg-pink-50/50 p-3">
            {sessions.map((session) => {
              const lastText = session.messages[session.messages.length - 1]?.text ?? ''
              const isActive = session.localId === activeSession?.localId
              return (
                <button
                  key={session.localId}
                  type="button"
                  onClick={() => setActiveSessionLocalId(session.localId)}
                  className={`w-full rounded-2xl border px-3 py-2 text-left shadow-sm transition ${
                    isActive
                      ? 'border-rose-300 bg-rose-50'
                      : 'border-pink-100 bg-white hover:bg-pink-50'
                  }`}
                >
                  <p className="truncate text-sm font-semibold text-rose-700">{session.title}</p>
                  <p className="mt-1 truncate text-xs text-rose-500">{lastText}</p>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-rose-400">
                    <span>{session.messages.length} messages</span>
                    <span>{session.updatedAt}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-pink-200/80 bg-white/90 shadow-xl backdrop-blur">
          <header className="border-b border-pink-100 bg-gradient-to-r from-rose-300/80 via-pink-300/70 to-fuchsia-200/70 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold text-rose-800">디딤 사내 RAG 챗봇</h1>
                <p className="text-sm text-rose-700">
                  사내 문서 검색과 기술 질의 응답을 위한 AI Assistant
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={clearAllHistory}
                  className="rounded-xl border border-rose-200 bg-white/85 px-3 py-1.5 text-xs font-semibold text-rose-700 shadow-sm hover:bg-rose-50"
                >
                  전체 히스토리 초기화
                </button>
                <span className="rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-rose-700">
                  {isLoading ? '응답 생성 중' : 'Ready'}
                </span>
              </div>
            </div>
          </header>

          <main className="flex-1 space-y-3 overflow-y-auto bg-gradient-to-b from-pink-50/80 to-white px-4 py-4">
            {activeMessages.map((message) => (
              <div
                key={message.id}
                className={`flex ${
                  message.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[82%] rounded-2xl px-4 py-3 shadow-md ${
                    message.sender === 'user'
                      ? 'rounded-br-md bg-gradient-to-r from-rose-500 to-pink-500 text-white'
                      : 'rounded-bl-md border border-pink-100 bg-white text-rose-800'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.text}</p>
                  <p
                    className={`mt-1 text-right text-[11px] ${
                      message.sender === 'user' ? 'text-pink-100' : 'text-rose-400'
                    }`}
                  >
                    {message.createdAt}
                  </p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md border border-pink-100 bg-white px-4 py-3 text-rose-700 shadow-md">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-rose-400" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-rose-400 [animation-delay:120ms]" />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-rose-400 [animation-delay:240ms]" />
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </main>

          <footer className="border-t border-pink-100 bg-white/95 p-4">
            <div className="flex items-center gap-2">
              <input
                className="flex-1 rounded-2xl border border-pink-200 bg-pink-50 px-4 py-3 outline-none ring-0 transition focus:border-rose-300 focus:ring-2 focus:ring-pink-200"
                placeholder="질문을 입력하세요..."
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
              />
              <button
                className="rounded-2xl bg-gradient-to-r from-rose-500 to-pink-500 px-5 py-3 font-medium text-white shadow-md transition hover:from-rose-600 hover:to-pink-600 disabled:cursor-not-allowed disabled:opacity-50"
                type="button"
                onClick={() => void sendMessage()}
                disabled={!input.trim() || Boolean(loadingSessionLocalId)}
              >
                전송
              </button>
            </div>
          </footer>
        </section>

        <aside className="hidden overflow-hidden rounded-2xl border border-pink-200/80 bg-white/90 shadow-xl backdrop-blur lg:flex lg:flex-col">
          <div className="border-b border-pink-100 bg-pink-100/60 px-4 py-3">
            <h2 className="text-sm font-semibold text-rose-700">세션 모니터링</h2>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-3 bg-pink-50/50 p-4 text-sm text-rose-800">
            <div className="rounded-2xl border border-pink-100 bg-white p-3 shadow-sm">
              <p className="text-xs text-rose-500">Session ID</p>
              <p className="mt-1 break-all font-medium">
                {activeSession?.sessionId ?? '아직 생성되지 않음'}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-2xl border border-pink-100 bg-white p-3 shadow-sm">
                <p className="text-xs text-rose-500">사용자</p>
                <p className="mt-1 text-base font-semibold">{activeUserMessages.length}</p>
              </div>
              <div className="rounded-2xl border border-pink-100 bg-white p-3 shadow-sm">
                <p className="text-xs text-rose-500">봇</p>
                <p className="mt-1 text-base font-semibold">{activeBotMessages.length}</p>
              </div>
            </div>
            <div className="rounded-2xl border border-pink-100 bg-white p-3 shadow-sm">
              <p className="text-xs text-rose-500">오류 로그</p>
              <p className="mt-1 font-semibold text-rose-600">{activeErrorCount}</p>
              <p className="mt-1 text-xs text-rose-400">현재 선택 세션 기준</p>
            </div>
            <div className="rounded-2xl border border-pink-100 bg-white p-3 shadow-sm">
              <p className="text-xs text-rose-500">API Endpoint</p>
              <p className="mt-1 break-all text-xs">{API_BASE_URL || '(same-origin)'}</p>
            </div>
            <div className="flex min-h-0 flex-1 flex-col rounded-2xl border border-pink-100 bg-white p-3 shadow-sm">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-xs text-rose-500">세션 로그</p>
                <span className="text-[11px] text-rose-400">{activeLogs.length} entries</span>
              </div>
              <div className="flex-1 space-y-2 overflow-y-auto pr-1">
                {activeLogs.length === 0 && (
                  <p className="text-xs text-rose-400">이 세션의 로그가 없습니다.</p>
                )}
                {[...activeLogs].reverse().map((log) => (
                  <div
                    key={log.id}
                    className={`rounded-xl border px-2 py-1.5 text-xs ${
                      log.level === 'error'
                        ? 'border-rose-200 bg-rose-50 text-rose-700'
                        : 'border-pink-100 bg-pink-50 text-rose-600'
                    }`}
                  >
                    <p className="font-semibold">
                      [{log.level.toUpperCase()}] {log.createdAt}
                    </p>
                    <p className="mt-0.5 break-words">{log.message}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default App
