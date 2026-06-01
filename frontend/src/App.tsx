import React, { useState, useEffect, useRef } from "react";
import {
  Phone, Mail, Info, X, RefreshCw, WifiOff, CheckCheck,
  Paperclip, Smile, AlertTriangle, Star, Eye, EyeOff, SendHorizontal,
  Mail as MailIcon, Volume2, VolumeX, ChevronLeft, ChevronRight
} from "lucide-react";
import { ChatSession, Operator, SenderRole } from "./types";
import { login } from "./api/auth";
import { getMe, setStatus } from "./api/operators";
import {
  listMyChats, listClosed, listPending, getHistory,
  acceptChat, rejectChat, closeChat, takeChat,
  mapAssignedChat, formatTime, PAGE_SIZE
} from "./api/chats";
import { loadSenderTypeMap } from "./api/senderTypes";
import { getToken, setToken, ApiError } from "./api/http";
import { OperatorSocket, ConnectionStatus } from "./realtime/operatorSocket";
import { playNotificationBeep } from "./util/sound";

// Ключи localStorage
const FULL_NAME_KEY = "support_full_name";
const SOUND_MUTED_KEY = "support_sound_muted";

export default function App() {
  // Авторизация
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
  const [loginUser, setLoginUser] = useState<string>("");
  const [loginPassword, setLoginPassword] = useState<string>("");
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState<boolean>(false);

  // Данные. Один массив: reserved+active (живут по WS) + текущая страница pending + текущая страница closed.
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null);
  const [currentOperator, setCurrentOperator] = useState<Operator | null>(null);

  // Пагинация серверных списков
  const [pendingPage, setPendingPage] = useState<number>(1);
  const [pendingTotal, setPendingTotal] = useState<number>(0);
  const [closedPage, setClosedPage] = useState<number>(1);
  const [closedTotal, setClosedTotal] = useState<number>(0);

  // UI
  const [messageInput, setMessageInput] = useState<string>("");
  const [isClientInfoOpen, setIsClientInfoOpen] = useState<boolean>(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [soundMuted, setSoundMuted] = useState<boolean>(
    () => localStorage.getItem(SOUND_MUTED_KEY) === "1"
  );

  // Связь
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<OperatorSocket | null>(null);
  const senderMapRef = useRef<Record<number, SenderRole>>({});
  const activeChatIdRef = useRef<number | null>(null);
  const operatorIdRef = useRef<number | null>(null);
  const soundMutedRef = useRef<boolean>(soundMuted);
  // Чаты, для которых история уже запрашивалась (ленивая подгрузка переписки).
  const loadedHistoryRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    activeChatIdRef.current = selectedChatId;
    scrollToBottom();
  }, [selectedChatId]);

  useEffect(() => {
    operatorIdRef.current = currentOperator?.id ?? null;
  }, [currentOperator]);

  useEffect(() => {
    soundMutedRef.current = soundMuted;
    localStorage.setItem(SOUND_MUTED_KEY, soundMuted ? "1" : "0");
  }, [soundMuted]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // --- Загрузка серверных страниц (pending/closed) ---
  const loadPending = async (page: number, search: string) => {
    try {
      const res = await listPending(page, search);
      setPendingPage(res.page);
      setPendingTotal(res.total);
      setChats((prev) => [...prev.filter((c) => c.status !== "pending"), ...res.items]);
    } catch (err) {
      console.error("Ошибка загрузки очереди:", err);
    }
  };

  const loadClosed = async (page: number, search: string) => {
    try {
      const res = await listClosed(operatorIdRef.current, page, search);
      setClosedPage(res.page);
      setClosedTotal(res.total);
      setChats((prev) => [...prev.filter((c) => c.status !== "closed"), ...res.items]);
    } catch (err) {
      console.error("Ошибка загрузки завершённых:", err);
    }
  };

  // --- Загрузка сессии оператора (после логина или при наличии токена) ---
  const initSession = async (fullName: string) => {
    senderMapRef.current = await loadSenderTypeMap();
    const me = await getMe();
    setCurrentOperator({
      id: me.id,
      fullName,
      status: me.status,
      activeChatsCount: me.activeChatsCount,
    });
    operatorIdRef.current = me.id;

    const myChats = await listMyChats(me.id);
    const withHistory = await Promise.all(
      myChats.map(async (c) => ({ ...c, messages: await getHistory(c.id, senderMapRef.current) }))
    );
    withHistory.forEach((c) => loadedHistoryRef.current.add(c.id));
    setChats(withHistory);
    if (withHistory.length > 0) {
      setSelectedChatId(withHistory[0].id);
    }
    // Страницы pending/closed подтянет debounce-эффект при isLoggedIn=true.
    connectSocket();
  };

  // Выбор чата: для завершённых/нераспределённых (и любых пустых) лениво подгружаем переписку.
  const selectChat = (chatId: number) => {
    setSelectedChatId(chatId);
    const chat = chats.find((c) => c.id === chatId);
    if (chat && chat.messages.length === 0 && !loadedHistoryRef.current.has(chatId)) {
      loadedHistoryRef.current.add(chatId);
      getHistory(chatId, senderMapRef.current)
        .then((messages) => {
          setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, messages } : c)));
          setTimeout(scrollToBottom, 100);
        })
        .catch((err) => console.error("Ошибка загрузки истории:", err));
    }
  };

  // Автологин по сохранённому токену
  useEffect(() => {
    if (getToken()) {
      const name = localStorage.getItem(FULL_NAME_KEY) ?? "";
      initSession(name)
        .then(() => setIsLoggedIn(true))
        .catch(() => {
          setToken(null);
          setIsLoggedIn(false);
        });
    }
    return () => {
      socketRef.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Поиск по pending/closed — серверный, с debounce. Reserved/active фильтруются клиентски.
  useEffect(() => {
    if (!isLoggedIn) return;
    const t = setTimeout(() => {
      loadPending(1, searchQuery);
      loadClosed(1, searchQuery);
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, isLoggedIn]);

  // --- WebSocket оператора ---
  const connectSocket = () => {
    const token = getToken();
    if (!token) return;
    socketRef.current?.close();

    const socket = new OperatorSocket(token, {
      onStatusChange: setConnectionStatus,
      onChatAssigned: (chatId, client) => {
        // upsert: заменяем возможный pending-элемент зарезервированным.
        setChats((prev) => [
          mapAssignedChat(chatId, client, operatorIdRef.current),
          ...prev.filter((c) => c.id !== chatId),
        ]);
        if (!soundMutedRef.current) playNotificationBeep();
      },
      onNewMessage: (message) => {
        setChats((prev) =>
          prev.map((c) => {
            if (c.id !== message.chatId) return c;
            if (c.messages.some((m) => m.id === message.id)) return c;
            return { ...c, messages: [...c.messages, message] };
          })
        );
        if (message.chatId === activeChatIdRef.current) {
          setTimeout(scrollToBottom, 100);
        }
      },
      onSessionClosed: (chatId) => {
        setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, status: "closed" } : c)));
      },
      onReconnected: () => {
        resyncChats();
      },
    });
    socket.connect();
    socketRef.current = socket;
  };

  // Досинхронизация после реконнекта
  const resyncChats = async () => {
    const operatorId = operatorIdRef.current;
    if (operatorId === null) return;
    try {
      const myChats = await listMyChats(operatorId);
      const withHistory = await Promise.all(
        myChats.map(async (c) => ({ ...c, messages: await getHistory(c.id, senderMapRef.current) }))
      );
      withHistory.forEach((c) => loadedHistoryRef.current.add(c.id));
      setChats((prev) => [
        ...withHistory,
        ...prev.filter((c) => c.status === "pending" || c.status === "closed"),
      ]);
      loadPending(pendingPage, searchQuery);
      loadClosed(closedPage, searchQuery);
    } catch (err) {
      console.error("Ошибка досинхронизации чатов:", err);
    }
  };

  // --- Логин ---
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginError(null);
    setLoginLoading(true);
    try {
      await login(loginUser, loginPassword);
      localStorage.setItem(FULL_NAME_KEY, loginUser);
      await initSession(loginUser);
      setIsLoggedIn(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setLoginError("Неверный логин или пароль");
      } else {
        setLoginError("Ошибка входа. Проверьте, что бэкенд доступен.");
      }
      setToken(null);
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    socketRef.current?.close();
    socketRef.current = null;
    setToken(null);
    localStorage.removeItem(FULL_NAME_KEY);
    setIsLoggedIn(false);
    setChats([]);
    setCurrentOperator(null);
    setSelectedChatId(null);
    setConnectionStatus("disconnected");
    loadedHistoryRef.current.clear();
  };

  // --- Статус оператора ---
  const handleStatusChange = async (online: boolean) => {
    try {
      const status = await setStatus(online);
      setCurrentOperator((prev) => (prev ? { ...prev, status } : prev));
    } catch (err) {
      console.error("Ошибка смены статуса:", err);
    }
  };

  // --- Действия с чатом ---
  const handleTakeChat = async (chatId: number) => {
    try {
      await takeChat(chatId);
      // Убираем из очереди; chat_assigned добавит чат в «Новые» (reserved).
      setChats((prev) => prev.filter((c) => !(c.id === chatId && c.status === "pending")));
      setPendingTotal((t) => Math.max(0, t - 1));
    } catch (err) {
      if (err instanceof ApiError) {
        alert(err.status === 409 ? "Чат уже взят или вы не в сети (статус «Онлайн»)." : err.message);
      }
      console.error("Ошибка взятия чата:", err);
    }
  };

  const handleAcceptChat = async (chatId: number) => {
    try {
      await acceptChat(chatId);
      setChats((prev) =>
        prev.map((c) =>
          c.id === chatId ? { ...c, status: "active", acceptedAt: new Date().toISOString() } : c
        )
      );
    } catch (err) {
      console.error("Ошибка принятия чата:", err);
    }
  };

  const handleRejectChat = async (chatId: number) => {
    try {
      await rejectChat(chatId);
      setChats((prev) => prev.filter((c) => c.id !== chatId));
      if (selectedChatId === chatId) setSelectedChatId(null);
    } catch (err) {
      console.error("Ошибка отклонения чата:", err);
    }
  };

  const handleCloseSession = async (chatId: number) => {
    try {
      await closeChat(chatId);
      setChats((prev) => prev.map((c) => (c.id === chatId ? { ...c, status: "closed" } : c)));
    } catch (err) {
      console.error("Ошибка закрытия чата:", err);
    }
  };

  // --- Отправка сообщения оператором (только в active; рендер придёт эхом) ---
  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!messageInput.trim() || selectedChatId === null) return;
    const chat = chats.find((c) => c.id === selectedChatId);
    if (!chat || chat.status !== "active") return;
    socketRef.current?.sendMessage(selectedChatId, messageInput.trim());
    setMessageInput("");
  };

  // Копирование в буфер
  const handleCopyToClipboard = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 1500);
  };

  // Производные данные
  const query = searchQuery.toLowerCase();
  const matchesClient = (c: ChatSession) =>
    c.customerName.toLowerCase().includes(query) || String(c.id).includes(searchQuery);

  // reserved/active — клиентский фильтр; pending/closed уже отфильтрованы сервером.
  const reservedChats = chats.filter((c) => c.status === "reserved" && matchesClient(c));
  const activeChats = chats.filter((c) => c.status === "active" && matchesClient(c));
  const pendingChats = chats.filter((c) => c.status === "pending");
  const closedChats = chats.filter((c) => c.status === "closed");
  const totalCount = chats.length;
  const currentChat = chats.find((c) => c.id === selectedChatId);

  const pendingPages = Math.max(1, Math.ceil(pendingTotal / PAGE_SIZE));
  const closedPages = Math.max(1, Math.ceil(closedTotal / PAGE_SIZE));

  // Пагинатор
  const renderPager = (page: number, pages: number, onPage: (p: number) => void) => {
    if (pages <= 1) return null;
    return (
      <div className="flex items-center justify-center gap-3 mt-3 text-[11px] text-gray-500 font-mono select-none">
        <button
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
        >
          <ChevronLeft size={14} />
        </button>
        <span>{page} / {pages}</span>
        <button
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] font-sans text-gray-900 flex flex-col antialiased">

      {!isLoggedIn ? (
        // Экран входа
        <div className="flex-1 flex items-center justify-center p-6 bg-[#F9FAFB] relative overflow-hidden">
          <div className="absolute top-[-20%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-blue-500/5 blur-3xl -z-10"></div>
          <div className="absolute bottom-[-20%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-emerald-500/5 blur-3xl -z-10"></div>

          <div id="login-container" className="grid grid-cols-1 md:grid-cols-12 max-w-4xl w-full bg-white rounded-2xl shadow-xl overflow-hidden min-h-[500px] border border-gray-150">
            {/* Брендинг */}
            <div className="md:col-span-5 bg-[#111827] text-white p-10 flex flex-col justify-between relative overflow-hidden">
              <div className="absolute top-0 right-0 w-[200px] h-[200px] bg-blue-500/10 rounded-full blur-2xl"></div>

              <div className="flex items-center gap-2 relative z-10">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg font-sans">S</div>
                <span className="font-semibold text-lg tracking-tight">SupportWay</span>
              </div>

              <div className="my-auto space-y-6 relative z-10 py-6">
                <div>
                  <h1 className="text-2xl font-bold leading-tight tracking-tight text-white mb-2">
                    Платформа поддержки клиентов
                  </h1>
                  <p className="text-gray-400 text-xs leading-relaxed max-w-xs">
                    Рабочее место оператора техподдержки с обменом сообщениями в реальном времени.
                  </p>
                </div>

                <div className="space-y-3.5 pt-4">
                  <div className="flex items-center gap-3">
                    <span className="text-blue-500 text-base">⚡</span>
                    <div>
                      <h4 className="font-semibold text-xs text-gray-200">Быстрые ответы</h4>
                      <p className="text-[11px] text-gray-400">Мгновенная доставка сообщений</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-blue-500 text-base">👤</span>
                    <div>
                      <h4 className="font-semibold text-xs text-gray-200">Единое окно</h4>
                      <p className="text-[11px] text-gray-400">Управляйте всеми диалогами прямо здесь</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-[#10B981] text-base">●</span>
                    <div>
                      <h4 className="font-semibold text-xs text-gray-200">Авто-балансировка</h4>
                      <p className="text-[11px] text-gray-400">Справедливое распределение запросов</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="text-[10px] text-gray-500 border-t border-gray-800/80 pt-4 font-mono">
                SupportWay
              </div>
            </div>

            {/* Форма входа */}
            <div className="md:col-span-7 p-10 flex flex-col justify-center">
              <div className="max-w-md w-full mx-auto space-y-6">
                <div>
                  <h2 className="text-xl font-bold text-gray-900 tracking-tight">Вход в систему</h2>
                  <p className="text-gray-500 text-xs mt-1">Введите ФИО и пароль для авторизации оператора</p>
                </div>

                <form className="space-y-4" onSubmit={handleLogin}>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block font-mono">ФИО</label>
                    <input
                      required
                      type="text"
                      value={loginUser}
                      onChange={(e) => setLoginUser(e.target.value)}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-250 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all text-sm text-gray-900"
                      placeholder="Иван Иванов"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block font-mono">Пароль</label>
                    <div className="relative">
                      <input
                        required
                        type={showPassword ? "text" : "password"}
                        value={loginPassword}
                        onChange={(e) => setLoginPassword(e.target.value)}
                        className="w-full px-4 py-2.5 bg-gray-50 border border-gray-250 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all text-sm text-gray-900"
                        placeholder="••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>

                  {loginError && (
                    <div className="text-xs text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 font-medium">
                      {loginError}
                    </div>
                  )}

                  <button
                    id="btn-login-submit"
                    type="submit"
                    disabled={loginLoading}
                    className="w-full py-3 bg-gray-900 hover:bg-gray-800 disabled:opacity-60 text-white font-bold rounded-lg transition-all text-xs uppercase tracking-wider cursor-pointer shadow-md"
                  >
                    {loginLoading ? "Вход..." : "Войти"}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden bg-[#F9FAFB]">

          {/* Шапка */}
          <header className="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shrink-0 select-none">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg font-sans">S</div>
              <h1 className="text-lg font-semibold tracking-tight text-gray-900 underline underline-offset-4 decoration-blue-500/30">SupportWay</h1>
            </div>

            <div className="flex items-center gap-3">
              {/* Переключатель звука */}
              <button
                id="btn-toggle-sound"
                onClick={() => setSoundMuted((m) => !m)}
                title={soundMuted ? "Включить звук уведомлений" : "Выключить звук уведомлений"}
                className={`p-2 rounded-full border transition-colors cursor-pointer ${
                  soundMuted
                    ? "bg-gray-50 border-gray-200 text-gray-400 hover:text-gray-600"
                    : "bg-blue-50 border-blue-100 text-blue-600 hover:bg-blue-100"
                }`}
              >
                {soundMuted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>

              <div className="flex items-center gap-3 bg-gray-50 border border-gray-100 rounded-full px-4 py-1.5">
                <div className="flex items-center gap-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${currentOperator?.status === "online" && connectionStatus === "connected" ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" : "bg-gray-300"}`}></span>
                  <span className="text-sm font-medium text-gray-600">
                    {currentOperator ? currentOperator.fullName || "Оператор" : "Оператор"} •{" "}
                    <select
                      id="select-operator-status"
                      value={currentOperator ? currentOperator.status : "offline"}
                      onChange={(e) => handleStatusChange(e.target.value === "online")}
                      className={`font-semibold bg-transparent border-none outline-none cursor-pointer p-0 m-0 ${
                        currentOperator?.status === "online" ? "text-emerald-600 font-bold" : "text-gray-500 font-bold"
                      }`}
                    >
                      <option value="online">Онлайн</option>
                      <option value="offline">Офлайн</option>
                    </select>
                  </span>
                </div>
                <div className="w-px h-4 bg-gray-300"></div>
                <button
                  id="btn-logout-header"
                  onClick={handleLogout}
                  className="text-sm font-medium text-red-500 hover:text-red-600 transition-colors cursor-pointer"
                >
                  Выйти
                </button>
              </div>
            </div>
          </header>

          {/* Контент */}
          <main className="flex flex-1 overflow-hidden">
            {/* Левая панель: список чатов */}
            <aside id="left-sidebar-operator" className="w-80 bg-white border-r border-gray-200 flex flex-col shrink-0">
              <div className="p-4 border-b border-gray-100 bg-white">
                <div className="relative">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Поиск по имени или #id..."
                    className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 text-gray-900 placeholder-gray-400 font-sans"
                  />
                  <span className="absolute left-3 top-2.5 text-sm opacity-40">🔍</span>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto divide-y divide-gray-50 bg-white">

                {/* Новые: reserved */}
                <div className="p-4">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-gray-400 mb-3 flex items-center gap-2 font-sans">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                    Новые ({reservedChats.length})
                  </h2>

                  {reservedChats.length === 0 ? (
                    <div className="p-4 text-center rounded-xl bg-gray-50 text-xs text-gray-400 border border-dashed border-gray-200 font-sans">
                      Нет новых обращений
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {reservedChats.map((chat) => {
                        const last = chat.messages[chat.messages.length - 1];
                        return (
                          <div
                            id={`chat-reserved-item-${chat.id}`}
                            key={chat.id}
                            onClick={() => selectChat(chat.id)}
                            className={`p-3 bg-amber-50 border border-amber-200 rounded-xl cursor-pointer shadow-sm relative transition-all duration-200 ${
                              selectedChatId === chat.id ? "ring-2 ring-amber-500 border-transparent shadow-md" : "pulsate-reserved-chat"
                            }`}
                          >
                            <div className="flex justify-between items-start mb-1 overflow-hidden">
                              <span className="font-bold text-sm text-gray-900 truncate pr-2 font-sans">{chat.customerName}</span>
                              <span className="text-[10px] bg-amber-200 text-amber-805 px-1.5 py-0.5 rounded font-bold shrink-0">NEW</span>
                            </div>
                            <p className="text-xs text-amber-900 opacity-80 line-clamp-1 mb-1 font-sans">
                              {last ? last.text : "Новое обращение"}
                            </p>
                            <div className="flex items-center justify-between text-[10px] text-gray-400 font-mono mt-1 pt-1 border-t border-amber-100/50">
                              <span>ID: #{chat.id}</span>
                              <span>{last ? formatTime(last.createdAt) : formatTime(chat.createdAt)}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* В работе: active */}
                <div className="p-4">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-[#9CA3AF] mb-3 font-sans">
                    В работе ({activeChats.length})
                  </h2>

                  {activeChats.length === 0 ? (
                    <div className="p-4 text-center rounded-xl bg-gray-50 text-xs text-gray-400 border border-dashed border-gray-200 font-sans">
                      Нет активных диалогов
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {activeChats.map((chat) => {
                        const isSelected = selectedChatId === chat.id;
                        const last = chat.messages[chat.messages.length - 1];
                        const isUnread = !!last && last.sender === "customer";
                        return (
                          <div
                            id={`chat-active-item-${chat.id}`}
                            key={chat.id}
                            onClick={() => selectChat(chat.id)}
                            className={`p-3 border transition-all duration-200 cursor-pointer rounded-xl ${
                              isSelected
                                ? "bg-blue-50 border-blue-100 shadow-sm"
                                : "bg-white border-transparent hover:bg-gray-50"
                            }`}
                          >
                            <div className="flex justify-between items-start mb-1">
                              <span className={`text-sm text-gray-900 truncate pr-2 font-sans ${isSelected || isUnread ? "font-bold" : "font-medium"}`}>{chat.customerName}</span>
                              <span className="text-[10px] text-gray-400 shrink-0 font-mono">{last ? formatTime(last.createdAt) : ""}</span>
                            </div>
                            <p className="text-xs text-gray-500 line-clamp-1 mb-1 font-sans">{last ? last.text : "Нет сообщений"}</p>
                            <div className="flex items-center justify-between gap-2 text-[10px] text-gray-400 font-mono">
                              <span>ID: #{chat.id}</span>
                              {isUnread ? (
                                <span className="bg-emerald-500 text-white font-sans text-[10px] px-1.5 py-0.5 rounded font-bold shrink-0">
                                  NEW
                                </span>
                              ) : (
                                <span className="text-gray-400 font-sans text-[10px]">В работе</span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Нераспределённые: pending */}
                <div className="p-4">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-[#9CA3AF] mb-3 flex items-center justify-between font-sans">
                    <span className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-violet-400"></span>
                      Нераспределённые ({pendingTotal})
                    </span>
                    <button
                      onClick={() => loadPending(pendingPage, searchQuery)}
                      title="Обновить очередь"
                      className="p-1 text-gray-400 hover:text-gray-700 cursor-pointer"
                    >
                      <RefreshCw size={12} />
                    </button>
                  </h2>

                  {pendingChats.length === 0 ? (
                    <div className="p-4 text-center rounded-xl bg-gray-50 text-xs text-gray-400 border border-dashed border-gray-200 font-sans">
                      Очередь пуста
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {pendingChats.map((chat) => {
                        const isSelected = selectedChatId === chat.id;
                        const last = chat.messages[chat.messages.length - 1];
                        return (
                          <div
                            id={`chat-pending-item-${chat.id}`}
                            key={chat.id}
                            onClick={() => selectChat(chat.id)}
                            className={`p-3 border transition-all duration-200 cursor-pointer rounded-xl ${
                              isSelected
                                ? "bg-violet-50 border-violet-200 shadow-sm"
                                : "bg-white border-gray-100 hover:bg-gray-50"
                            }`}
                          >
                            <div className="flex justify-between items-start mb-1">
                              <span className="text-sm text-gray-900 truncate pr-2 font-sans font-medium">{chat.customerName}</span>
                              <span className="text-[10px] text-gray-400 shrink-0 font-mono">{formatTime(chat.createdAt)}</span>
                            </div>
                            <p className="text-xs text-gray-500 line-clamp-1 mb-2 font-sans">{last ? last.text : "Ожидает оператора"}</p>
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-[10px] text-gray-400 font-mono">ID: #{chat.id}</span>
                              <button
                                id={`btn-take-${chat.id}`}
                                onClick={(e) => { e.stopPropagation(); handleTakeChat(chat.id); }}
                                className="text-[10px] font-bold px-2 py-1 rounded-md bg-violet-600 text-white hover:bg-violet-700 transition-colors cursor-pointer font-sans"
                              >
                                Взять
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {renderPager(pendingPage, pendingPages, (p) => loadPending(p, searchQuery))}
                </div>

                {/* Завершённые: closed */}
                <div className="p-4">
                  <h2 className="text-xs font-bold uppercase tracking-widest text-[#9CA3AF] mb-3 font-sans">
                    Завершённые ({closedTotal})
                  </h2>

                  {closedChats.length === 0 ? (
                    <div className="p-4 text-center rounded-xl bg-gray-50 text-xs text-gray-400 border border-dashed border-gray-200 font-sans">
                      Нет завершённых диалогов
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {closedChats.map((chat) => {
                        const isSelected = selectedChatId === chat.id;
                        const last = chat.messages[chat.messages.length - 1];
                        return (
                          <div
                            id={`chat-closed-item-${chat.id}`}
                            key={chat.id}
                            onClick={() => selectChat(chat.id)}
                            className={`p-3 border transition-all duration-200 cursor-pointer rounded-xl ${
                              isSelected
                                ? "bg-gray-100 border-gray-200 shadow-sm"
                                : "bg-white border-transparent hover:bg-gray-50 opacity-80"
                            }`}
                          >
                            <div className="flex justify-between items-start mb-1">
                              <span className="text-sm text-gray-700 truncate pr-2 font-sans font-medium">{chat.customerName}</span>
                              <span className="text-[10px] text-gray-400 shrink-0 font-mono">{chat.closedAt ? formatTime(chat.closedAt) : ""}</span>
                            </div>
                            <p className="text-xs text-gray-500 line-clamp-1 mb-1 font-sans">{last ? last.text : "Завершённый диалог"}</p>
                            <div className="flex items-center justify-between gap-2 text-[10px] text-gray-400 font-mono">
                              <span>ID: #{chat.id}</span>
                              {chat.rating ? (
                                <span className="flex items-center gap-0.5 text-amber-500 font-sans">
                                  {chat.rating} <Star size={9} className="fill-amber-400 text-amber-400" />
                                </span>
                              ) : (
                                <span className="text-gray-400 font-sans text-[10px]">Закрыт</span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {renderPager(closedPage, closedPages, (p) => loadClosed(p, searchQuery))}
                </div>

              </div>

              <div className="p-4 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 flex items-center justify-between font-mono shrink-0 select-none">
                <span className="flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                  Всего: {totalCount} чатов
                </span>
                {connectionStatus === "connected" ? (
                  <span className="flex items-center gap-1 text-emerald-600">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                    Подключено
                  </span>
                ) : connectionStatus === "reconnecting" ? (
                  <span className="flex items-center gap-1 text-amber-600 font-bold">
                    <RefreshCw size={11} className="animate-spin" /> Переподключение
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-red-500 font-semibold">
                    <WifiOff size={11} /> Офлайн
                  </span>
                )}
              </div>
            </aside>

            {/* Центр: рабочая область */}
            <div className="flex-1 bg-[#F9FAFB] flex flex-col relative overflow-hidden">
              {currentChat ? (
                <>
                  {/* Шапка чата */}
                  <div id="chat-session-header" className="px-6 py-4 border-b border-gray-150 flex items-center justify-between bg-white z-10 shadow-xs shrink-0 select-none">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center font-bold text-blue-600 font-sans text-sm tracking-tight select-none shrink-0">
                        {currentChat.customerName.substring(0, 1).toUpperCase()}
                      </div>
                      <div>
                        <h2 className="font-bold text-gray-950 flex items-center gap-2 text-sm leading-none font-sans">
                          {currentChat.customerName}
                          <span className="text-[10px] text-gray-400 font-mono font-normal">#{currentChat.id}</span>
                        </h2>
                        <div className="flex items-center gap-1.5 mt-1.5">
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded tracking-wider ${
                            currentChat.status === "active"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-150"
                              : currentChat.status === "reserved"
                              ? "bg-amber-50 text-amber-700 animate-pulse border border-amber-150"
                              : currentChat.status === "pending"
                              ? "bg-violet-50 text-violet-700 border border-violet-150"
                              : "bg-red-50 text-red-700 border border-red-150"
                          }`}>
                            {currentChat.status === "active"
                              ? "В РАБОТЕ"
                              : currentChat.status === "reserved"
                              ? "РЕЗЕРВ"
                              : currentChat.status === "pending"
                              ? "В ОЧЕРЕДИ"
                              : "ЗАКРЫТ"}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        id="btn-customer-info"
                        onClick={() => setIsClientInfoOpen(true)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 hover:bg-gray-100 text-xs font-semibold text-gray-700 rounded-lg border border-gray-205 transition-colors cursor-pointer font-sans"
                      >
                        <Info size={13} />
                        Инфо
                      </button>

                      {currentChat.status !== "closed" && currentChat.status !== "pending" && (
                        <button
                          id="btn-close-session"
                          onClick={() => handleCloseSession(currentChat.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-50 hover:bg-red-100 text-xs font-bold text-red-650 rounded-lg border border-red-100 transition-colors cursor-pointer font-sans"
                        >
                          <X size={13} />
                          Закрыть
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Баннер потери связи */}
                  {connectionStatus !== "connected" && (
                    <div className="bg-amber-50 border-b border-amber-200 text-amber-800 px-6 py-2.5 text-xs flex items-center justify-center gap-2 font-medium shrink-0 animate-pulse font-sans">
                      <AlertTriangle size={14} className="shrink-0 text-amber-500" />
                      <span>Связь с сервером прервана. Идёт переподключение...</span>
                    </div>
                  )}

                  {/* Рабочая область сообщений */}
                  <div className="flex-1 overflow-y-auto p-6 bg-[#F9FAFB] flex flex-col space-y-4">

                    {currentChat.status === "reserved" ? (
                      // Экран приёма зарезервированного чата
                      <div id="reserved-action-overlay" className="my-auto max-w-md w-full mx-auto bg-white p-8 rounded-3xl border border-gray-150 shadow-xl space-y-6">
                        <div className="text-center space-y-3">
                          <div className="h-14 w-14 mx-auto rounded-full bg-amber-50 border border-amber-100 flex items-center justify-center text-amber-500 animate-pulse">
                            <AlertTriangle size={24} />
                          </div>
                          <div className="space-y-1">
                            <h3 className="text-lg font-bold text-gray-900 font-sans tracking-tight">Новое входящее обращение</h3>
                            <p className="text-gray-500 text-xs leading-relaxed font-sans">
                              Нажмите «Принять», чтобы войти в диалог, или «Отклонить» для перебалансировки.
                            </p>
                          </div>
                        </div>

                        {/* Контакты клиента */}
                        <div className="p-4 rounded-xl bg-gray-55 border border-gray-150 text-left space-y-2.5 text-xs">
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <span className="text-gray-400 block text-[9px] uppercase font-bold font-mono">Почта</span>
                              <span className="text-gray-700 block mt-0.5 font-medium truncate font-sans">{currentChat.customerEmail || "—"}</span>
                            </div>
                            <div>
                              <span className="text-gray-400 block text-[9px] uppercase font-bold font-mono">Телефон</span>
                              <span className="text-gray-700 block mt-0.5 font-medium font-sans">{currentChat.customerPhone || "—"}</span>
                            </div>
                          </div>
                        </div>

                        {/* Сообщения, присланные клиентом до принятия */}
                        {currentChat.messages.length > 0 && (
                          <div className="space-y-2">
                            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider font-mono">Сообщения клиента</div>
                            <div className="max-h-48 overflow-y-auto space-y-2 p-3 bg-gray-50 border border-gray-150 rounded-xl">
                              {currentChat.messages.map((msg, index) => (
                                <div key={`${msg.id}-${index}`} className="flex flex-col items-start">
                                  <div className="bg-white border border-gray-150 rounded-2xl rounded-bl-none px-3 py-2 text-xs text-gray-800 max-w-[85%] shadow-xs">
                                    <p className="leading-relaxed whitespace-pre-line font-sans">{msg.text}</p>
                                    <span className="block text-right text-[9px] text-gray-400 font-mono mt-0.5">{formatTime(msg.createdAt)}</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="flex flex-col gap-2.5">
                          <button
                            id="btn-reserved-accept"
                            onClick={() => handleAcceptChat(currentChat.id)}
                            className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-2xl transition-all shadow-md shadow-emerald-100 cursor-pointer text-xs font-sans"
                          >
                            Принять и начать сессию
                          </button>

                          <button
                            id="btn-reserved-reject"
                            onClick={() => handleRejectChat(currentChat.id)}
                            className="w-full py-2.5 bg-white border border-gray-250 hover:bg-gray-50 text-gray-500 font-semibold rounded-2xl transition-all cursor-pointer text-xs font-sans"
                          >
                            Отклонить
                          </button>
                        </div>
                      </div>
                    ) : currentChat.status === "pending" ? (
                      // Просмотр нераспределённого чата
                      <div className="my-auto max-w-sm w-full mx-auto bg-white p-8 rounded-3xl border border-gray-150 shadow-xl text-center space-y-5">
                        <div className="h-14 w-14 mx-auto rounded-full bg-violet-50 border border-violet-100 flex items-center justify-center text-violet-500">
                          <AlertTriangle size={24} />
                        </div>
                        <div className="space-y-1">
                          <h3 className="text-lg font-bold text-gray-900 font-sans tracking-tight">Обращение в очереди</h3>
                          <p className="text-gray-500 text-xs leading-relaxed font-sans">
                            Чат ещё не распределён. Возьмите его в работу, чтобы начать диалог.
                          </p>
                        </div>

                        {currentChat.messages.length > 0 && (
                          <div className="max-h-40 overflow-y-auto space-y-2 p-3 bg-gray-50 border border-gray-150 rounded-xl text-left">
                            {currentChat.messages.map((msg, index) => (
                              <div key={`${msg.id}-${index}`} className="bg-white border border-gray-150 rounded-xl px-3 py-2 text-xs text-gray-800">
                                <p className="leading-relaxed whitespace-pre-line font-sans">{msg.text}</p>
                                <span className="block text-right text-[9px] text-gray-400 font-mono mt-0.5">{formatTime(msg.createdAt)}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        <button
                          onClick={() => handleTakeChat(currentChat.id)}
                          className="w-full py-3 bg-violet-600 hover:bg-violet-700 text-white font-bold rounded-2xl transition-all shadow-md cursor-pointer text-xs font-sans"
                        >
                          Взять в работу
                        </button>
                      </div>
                    ) : (
                      // Лента сообщений (active/closed)
                      <div className="messages-flow-zone flex-1 flex flex-col justify-end min-h-0">
                        <div className="space-y-4">
                          <div className="flex items-center justify-center">
                            <span className="px-3 py-1 bg-white border border-gray-100 text-[10px] font-semibold text-gray-400 uppercase rounded-full tracking-wider shadow-sm">
                              Сегодня
                            </span>
                          </div>

                          {currentChat.messages.map((msg, index) => {
                            if (msg.sender === "system") {
                              return (
                                <div key={`${msg.id}-${index}`} className="flex items-center justify-center p-2 text-center">
                                  <span className="bg-gray-100 text-gray-500 rounded-lg px-3 py-1 text-xs max-w-md italic border border-gray-200">
                                    {msg.text}
                                  </span>
                                </div>
                              );
                            }

                            const isOp = msg.sender === "operator";
                            return (
                              <div
                                key={`${msg.id}-${index}`}
                                className={`flex flex-col ${isOp ? "items-end" : "items-start"} message-bubble-entrance`}
                              >
                                <div className="flex items-end gap-2 max-w-[70%]">
                                  {!isOp && (
                                    <div className="h-7 w-7 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-[10px] text-blue-600 font-bold shrink-0 select-none">
                                      {currentChat.customerName.substring(0, 1).toUpperCase()}
                                    </div>
                                  )}
                                  <div className={`relative px-4 py-2.5 rounded-2xl shadow-xs text-sm ${
                                    isOp
                                      ? "bg-blue-50/50 text-gray-950 rounded-br-none border border-blue-100/70"
                                      : "bg-white text-gray-950 rounded-bl-none border border-gray-150"
                                  }`}>
                                    <p className="leading-relaxed whitespace-pre-line font-sans">{msg.text}</p>

                                    <div className="flex items-center justify-end gap-1 mt-1 border-t border-gray-100/30 pt-1 select-none">
                                      <span className="text-[9px] text-gray-400 font-mono font-normal">
                                        {formatTime(msg.createdAt)}
                                      </span>
                                      {isOp && (
                                        <CheckCheck size={11} className="text-blue-500 shrink-0" />
                                      )}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            );
                          })}

                          <div ref={messagesEndRef} />
                        </div>
                      </div>
                    )}

                  </div>

                  {/* Поле ввода / экран закрытого чата */}
                  {currentChat.status === "active" ? (
                    <form
                      id="form-send-message"
                      onSubmit={handleSendMessage}
                      className="p-4 border-t border-gray-150 bg-white flex items-center gap-3 shrink-0"
                    >
                      <button
                        type="button"
                        className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
                        title="Приложить файл"
                      >
                        <Paperclip size={16} />
                      </button>

                      <input
                        id="input-chat-textbox"
                        type="text"
                        value={messageInput}
                        onChange={(e) => setMessageInput(e.target.value)}
                        placeholder="Напишите ответ клиенту..."
                        className="flex-1 bg-gray-50 border border-gray-200 rounded-xl px-4 py-2 text-xs leading-normal text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition-all font-sans"
                      />

                      <button
                        type="button"
                        className="p-2 text-gray-400 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors cursor-pointer"
                        title="Выбрать эмодзи"
                      >
                        <Smile size={16} />
                      </button>

                      <button
                        id="btn-send-message"
                        type="submit"
                        disabled={!messageInput.trim()}
                        className={`p-2 rounded-xl transition-all cursor-pointer shrink-0 ${
                          messageInput.trim()
                            ? "bg-blue-600 text-white shadow-md hover:bg-blue-700"
                            : "bg-gray-100 text-gray-300 cursor-not-allowed"
                        }`}
                      >
                        <SendHorizontal size={16} />
                      </button>
                    </form>
                  ) : currentChat.status === "closed" ? (
                    <div id="closed-feedback-section" className="p-6 bg-[#FAFBFD] border-t border-gray-150 text-center space-y-3.5 shrink-0">
                      <div className="text-gray-500 text-xs font-medium font-sans">Сессия обслуживания завершена.</div>

                      {currentChat.rating ? (
                        <div className="flex items-center justify-center gap-1 font-sans">
                          <span className="text-xs text-gray-400">Оценка клиента:</span>
                          <div className="flex items-center gap-0.5 ml-1">
                            {[1, 2, 3, 4, 5].map((s) => (
                              <Star
                                key={s}
                                size={13}
                                className={s <= currentChat.rating! ? "fill-amber-400 text-amber-405" : "text-gray-200"}
                              />
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                </>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[#F9FAFB] text-center space-y-3 select-none">
                  <div className="h-12 w-12 rounded-2xl bg-gray-50 border border-gray-150 flex items-center justify-center text-gray-400">
                    <MailIcon size={20} />
                  </div>
                  <h3 className="text-sm font-bold text-gray-900 font-sans">Выберите диалог</h3>
                  <p className="text-xs text-gray-400 max-w-xs leading-relaxed font-sans">
                    Выберите диалог в левой панели для начала консультирования.
                  </p>
                </div>
              )}
            </div>

          </main>

          {/* Модалка карточки клиента */}
          {isClientInfoOpen && currentChat && (
            <div id="customer-modal-overlay" className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div
                id="customer-modal-content"
                className="bg-white rounded-2xl max-w-sm w-full shadow-2xl overflow-hidden border border-gray-100 modal-appear-animation"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="p-5 bg-gradient-to-r from-[#26215D] to-[#43399F] text-white flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-base leading-tight">{currentChat.customerName}</h3>
                    <span className="text-[10px] text-indigo-200 uppercase tracking-widest font-bold">Карточка клиента #{currentChat.id}</span>
                  </div>
                  <button
                    onClick={() => setIsClientInfoOpen(false)}
                    className="p-1 hover:bg-white/10 rounded-full transition-colors text-white cursor-pointer"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="p-5 space-y-4">

                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-gray-400 uppercase block tracking-wider">Мобильный телефон</span>
                    <div className="flex items-center justify-between gap-2 p-2.5 bg-gray-50 border border-gray-100 rounded-xl">
                      <div className="flex items-center gap-2 text-sm text-gray-800">
                        <Phone size={14} className="text-gray-400" />
                        <span className="font-medium font-mono">{currentChat.customerPhone || "—"}</span>
                      </div>
                      {currentChat.customerPhone && (
                        <button
                          onClick={() => handleCopyToClipboard(currentChat.customerPhone!, "phone")}
                          className={`text-[10px] font-bold px-2 py-1 rounded transition-all cursor-pointer ${
                            copiedField === "phone"
                              ? "bg-green-100 text-green-700"
                              : "bg-white hover:bg-gray-100 text-indigo-600 border border-gray-200 shadow-sm"
                          }`}
                        >
                          {copiedField === "phone" ? "Скопировано!" : "Копировать"}
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <span className="text-[10px] font-bold text-gray-400 uppercase block tracking-wider">Рабочий Email</span>
                    <div className="flex items-center justify-between gap-2 p-2.5 bg-gray-50 border border-gray-100 rounded-xl">
                      <div className="flex items-center gap-2 text-sm text-gray-800">
                        <Mail size={14} className="text-gray-400" />
                        <span className="font-medium truncate">{currentChat.customerEmail || "—"}</span>
                      </div>
                      {currentChat.customerEmail && (
                        <button
                          onClick={() => handleCopyToClipboard(currentChat.customerEmail!, "email")}
                          className={`text-[10px] font-bold px-2 py-1 rounded transition-all cursor-pointer ${
                            copiedField === "email"
                              ? "bg-green-100 text-green-700"
                              : "bg-white hover:bg-gray-100 text-indigo-600 border border-gray-200 shadow-sm"
                          }`}
                        >
                          {copiedField === "email" ? "Скопировано!" : "Копировать"}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Источник обращения */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-gray-400 uppercase block tracking-wider">Проект</span>
                      <div className="p-2.5 bg-gray-50 border border-gray-100 rounded-xl text-sm text-gray-800 font-medium truncate">
                        {currentChat.source || "—"}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[10px] font-bold text-gray-400 uppercase block tracking-wider">ID в проекте</span>
                      <div className="p-2.5 bg-gray-50 border border-gray-100 rounded-xl text-sm text-gray-800 font-medium font-mono truncate">
                        {currentChat.externalId || "—"}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => setIsClientInfoOpen(false)}
                    className="w-full py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold rounded-xl text-xs transition-colors cursor-pointer mt-2"
                  >
                    Закрыть карточку
                  </button>

                </div>
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
