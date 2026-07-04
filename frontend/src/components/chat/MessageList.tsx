import { useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import type { Message } from '../../types';
import { formatTime } from '../ui/Time';

interface Props {
  messages: Message[];
  typing: boolean;
}

export function MessageList({ messages, typing }: Props) {
  const { user } = useAuth();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  if (!messages.length) {
    return (
      <div className="empty-state" style={{ padding: 20 }}>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>No messages yet. Say hello!</p>
      </div>
    );
  }

  return (
    <>
      {messages.map(m => {
        const isSent = m.sender_id === user?.id;

        if (m.deleted_at) {
          return (
            <div key={m.id} className="message deleted">
              <span>This message was deleted</span>
              <div className="msg-time">{formatTime(m.created_at)}</div>
            </div>
          );
        }

        return (
          <div key={m.id} className={`message ${isSent ? 'sent' : 'received'}`}>
            <div className="msg-text">{m.content}</div>
            <div className="msg-time">{formatTime(m.created_at)}</div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </>
  );
}
