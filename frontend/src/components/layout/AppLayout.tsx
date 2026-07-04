import { useState, useCallback, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import { useWebSocket } from '../../hooks/useWebSocket';
import type { Conversation, Message, User } from '../../types';
import { ConversationList } from '../chat/ConversationList';
import { MessageList } from '../chat/MessageList';
import { MessageInput } from '../chat/MessageInput';
import { SearchResultList } from '../ui/SearchResultList';
import { Avatar } from '../ui/Avatar';
import { showToast } from '../ui/Toast';

export function AppLayout() {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [_activePartnerId, setActivePartnerId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [typing, setTyping] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const typingTimeout = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const loadConversations = useCallback(async () => {
    const res = await api.getConversations();
    if (res.status === 200 && res.body) setConversations(res.body.conversations);
  }, []);

  const loadMessages = useCallback(async (convId: number) => {
    const res = await api.getMessages(convId);
    if (res.status === 200 && res.body) setMessages(res.body);
  }, []);

  useEffect(() => { loadConversations(); }, [loadConversations]);

  const handleWSMessage = useCallback((data: any) => {
    if (data.type === 'new_message' && data.message) {
      const msg = data.message;
      if (msg.conversation_id === activeConvId && msg.sender_id !== user?.id) {
        setMessages(prev => [...prev, {
          id: msg.id,
          conversation_id: msg.conversation_id,
          sender_id: msg.sender_id,
          content: msg.content,
          created_at: msg.created_at,
        }]);
      }
      loadConversations();
    }
    if (data.type === 'typing') {
      if (data.conversation_id === activeConvId && data.user_id !== user?.id) {
        setTyping(true);
        clearTimeout(typingTimeout.current);
        typingTimeout.current = setTimeout(() => setTyping(false), 2000);
      }
    }
  }, [activeConvId, user?.id, loadConversations]);

  const { send: _wsSend } = useWebSocket(handleWSMessage);

  const handleSelectConversation = useCallback(async (convId: number, partnerId: number) => {
    setActiveConvId(convId);
    setActivePartnerId(partnerId);
    setSidebarOpen(false);
    await loadMessages(convId);
  }, [loadMessages]);

  const handleSendMessage = useCallback(async (content: string) => {
    if (!activeConvId) return;
    // Optimistic
    const temp: Message = {
      id: -Date.now(),
      conversation_id: activeConvId,
      sender_id: user!.id,
      content,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, temp]);
    const res = await api.sendMessage(activeConvId, content);
    if (res.status === 201) {
      setMessages(prev => prev.map(m => m.id === temp.id && res.body ? res.body : m));
      loadConversations();
    } else {
      setMessages(prev => prev.filter(m => m.id !== temp.id));
      showToast('Failed to send message', 'error');
    }
  }, [activeConvId, user, loadConversations]);

  const handleSearch = useCallback(async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) { setSearchResults([]); return; }
    const res = await api.searchUsers(q);
    if (res.status === 200 && res.body) setSearchResults(res.body.users || []);
    else setSearchResults([]);
  }, []);

  const handleStartConversation = useCallback(async (userId: number, _username: string) => {
    const existing = conversations.find(c =>
      c.participants?.some(p => p.id === userId)
    );
    if (existing) {
      handleSelectConversation(existing.id, userId);
      return;
    }
    const res = await api.createConversation(userId);
    if (res.status === 200 || res.status === 201) {
      await loadConversations();
      setSearchResults([]);
      setSearchQuery('');
      handleSelectConversation(res.body!.id, userId);
    } else {
      showToast('Cannot start conversation', 'error');
    }
  }, [conversations, loadConversations, handleSelectConversation]);

  const partner = activeConvId
    ? conversations.find(c => c.id === activeConvId)?.participants?.find(p => p.id !== user?.id)
    : null;

  return (
    <div className="app-layout">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-user">
            <Avatar name={user?.display_name || user?.username || '?'} />
            <div className="sidebar-user-info">
              <span className="sidebar-user-name">{user?.display_name || user?.username}</span>
              <span className="sidebar-user-handle">@{user?.username}</span>
            </div>
          </div>
          <button className="btn-icon" onClick={logout} title="Logout">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>

        <div className="search-box">
          <div className="input-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input type="text" placeholder="Search users..." value={searchQuery} onChange={e => handleSearch(e.target.value)} />
          </div>
          {searchResults.length > 0 && (
            <SearchResultList users={searchResults} onSelect={handleStartConversation} />
          )}
        </div>

        <div className="sidebar-content">
          <ConversationList
            conversations={conversations}
            activeId={activeConvId}
            onSelect={handleSelectConversation}
          />
        </div>
      </aside>

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      <main className="main-panel">
        {!activeConvId ? (
          <div className="welcome-screen">
            <div className="welcome-content">
              <div className="welcome-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              </div>
              <h2>Welcome to Octane</h2>
              <p>Select a conversation or search for someone to chat with</p>
            </div>
          </div>
        ) : (
          <div className="chat-view">
            <div className="chat-header">
              <button className="btn-icon mobile-only" onClick={() => setSidebarOpen(true)}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
              </button>
              <div className="chat-header-info">
                <Avatar name={partner?.display_name || partner?.username || '?'} size="small" />
                <div>
                  <span className="chat-header-name">{partner?.display_name || partner?.username}</span>
                  <span className="chat-header-status">@{partner?.username}</span>
                </div>
              </div>
              <div className="chat-header-actions">
                <button className="btn-icon" title="Follow">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
                </button>
              </div>
            </div>

            <div className="messages-area">
              <div className="messages-list">
                <MessageList messages={messages} typing={typing} />
              </div>
            </div>

            <MessageInput onSend={handleSendMessage} />
          </div>
        )}
      </main>
    </div>
  );
}
