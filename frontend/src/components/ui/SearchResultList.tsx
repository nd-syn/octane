interface UserResult {
  id: number;
  username: string;
  display_name?: string;
}

interface Props {
  users: UserResult[];
  onSelect: (userId: number, username: string) => void;
}

export function SearchResultList({ users, onSelect }: Props) {
  return (
    <div className="search-results" style={{ display: 'block' }}>
      {users.map(u => (
        <div key={u.id} className="user-result" onClick={() => onSelect(u.id, u.username)}>
          <div className="avatar small">{(u.display_name || u.username)[0].toUpperCase()}</div>
          <div className="ur-info">
            <div className="ur-name">{u.display_name || u.username}</div>
            <div className="ur-handle">@{u.username}</div>
          </div>
          <div className="ur-action">
            <button>Chat</button>
          </div>
        </div>
      ))}
    </div>
  );
}
