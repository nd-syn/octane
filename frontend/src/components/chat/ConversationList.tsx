import { useAuth } from '../../context/AuthContext';
import type { Conversation } from '../../types';
import { Avatar } from '../ui/Avatar';
import { formatTime } from '../ui/Time';

interface Props {
  conversations: Conversation[];
  activeId: number | null;
  onSelect: (id: number, partnerId: number) => void;
}

export function ConversationList({ conversations, activeId, onSelect }: Props) {
  const { user } = useAuth();
  if (!conversations.length) {
    return (
      <div className="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        <p>No conversations yet</p>
        <span>Search users to start chatting</span>
      </div>
    );
  }

  return (
    <>
      {conversations.map(c => {
        const partner = c.participants?.find(p => p.id !== user?.id) || c.participants?.[0];
        const name = partner?.display_name || partner?.username || 'Unknown';
        return (
          <div
            key={c.id}
            className={`conv-item ${c.id === activeId ? 'active' : ''}`}
            onClick={() => partner && onSelect(c.id, partner.id)}
          >
            <Avatar name={name} size="small" />
            <div className="conv-info">
              <div className="conv-name">{name}</div>
              <div className="conv-preview">{c.last_message || ''}</div>
            </div>
            <div className="conv-meta">
              <span className="conv-time">{formatTime(c.last_message_at)}</span>
              {c.unread_count > 0 && <span className="unread-badge">{c.unread_count > 9 ? '9+' : c.unread_count}</span>}
            </div>
          </div>
        );
      })}
    </>
  );
}
