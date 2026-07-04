export interface User {
  id: number;
  username: string;
  email?: string;
  display_name?: string;
  bio?: string;
  avatar_url?: string;
  created_at: string;
}

export interface Conversation {
  id: number;
  participants: User[];
  last_message?: string;
  last_message_at?: string;
  unread_count: number;
  created_at: string;
}

export interface Message {
  id: number;
  conversation_id: number;
  sender_id: number;
  sender?: User;
  content: string;
  created_at: string;
  edited_at?: string;
  deleted_at?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

export interface ApiError {
  error: string;
  detail: string;
}
